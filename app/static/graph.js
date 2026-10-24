/*
 * RiskGraph topology renderer.
 * Plain JavaScript, no dependencies, CSP-safe: no eval, no inline handlers,
 * no style injection. All visual state is expressed through classes and SVG
 * attributes. All saved text is written with textContent.
 *
 * Public API (window.RiskGraphView):
 *   mountTopology(container, {onNodeSelect})        -> topology controller
 *     .setTrace(trace, caseRecord, configuration)
 *     .setPlayback({eventIndex, progress, playing, reducedMotion})
 *     .selectNode(visualId | null)
 *   mountModel(container, {onScenarioSelect, onWeightsOpen}) -> model controller
 *     .setAnalysis(analysis, {configuration, scenario, weights, labels, densityFor})
 *   renderPathThumb(svg, trace, configuration)
 *   renderDensity(svg, cell, density)
 *   renderIntervals(svg, projections, {order, labels, selected})
 *   VISUAL_NODES, CONFIG_EDGES, nodeStatus(...)
 */
'use strict';
(function (global) {
  const NS = 'http://www.w3.org/2000/svg';

  function s(tag, attrs, parent) {
    const n = document.createElementNS(NS, tag);
    if (attrs) for (const k of Object.keys(attrs)) {
      const v = attrs[k];
      if (v === null || v === undefined || v === false) continue;
      if (k === 'text') n.textContent = String(v);
      else n.setAttribute(k, String(v));
    }
    if (parent) parent.appendChild(n);
    return n;
  }
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  const fmt = (x, d = 1) => Number(x).toFixed(d);

  /* ------------------------------------------------------------------ */
  /* Canonical topology                                                  */
  /* ------------------------------------------------------------------ */

  // Visual nodes. `canonical` is the event node ID in the saved trace.
  // msg and rec are two visual ports of the single canonical request event.
  const VISUAL_NODES = [
    { id: 'msg', canonical: 'request', kind: 'input-untrusted', label: 'Customer message', role: 'Untrusted input' },
    { id: 'rec', canonical: 'request', kind: 'input-trusted', label: 'Order record', role: 'Trusted synthetic record' },
    { id: 'request', canonical: 'request', kind: 'hub', label: 'Request', role: 'Request' },
    { id: 'actor', canonical: 'actor', kind: 'agent', label: 'Refund agent', role: 'Agent' },
    { id: 'reviewer', canonical: 'reviewer', kind: 'agent', label: 'Reviewer', role: 'Agent' },
    { id: 'rules', canonical: 'rules', kind: 'det', label: 'Policy rules', role: 'Deterministic check' },
    { id: 'payment', canonical: 'payment', kind: 'tool', label: 'Payment', role: 'Deterministic simulated tool' },
    { id: 'evaluator', canonical: 'evaluator', kind: 'eval', label: 'Evaluator', role: 'Deterministic scoring' },
  ];
  const VN = Object.fromEntries(VISUAL_NODES.map(n => [n.id, n]));

  // Structural control-flow edges permitted by each configuration.
  // These match the union of executed edges in the saved bundle.
  const CONFIG_EDGES = {
    none: [['request', 'actor'], ['actor', 'payment'], ['actor', 'evaluator'], ['payment', 'evaluator']],
    rules: [['request', 'actor'], ['actor', 'rules'], ['rules', 'payment'], ['rules', 'evaluator'], ['payment', 'evaluator']],
    reviewer: [['request', 'actor'], ['actor', 'reviewer'], ['reviewer', 'payment'], ['reviewer', 'evaluator'], ['payment', 'evaluator']],
    both: [['request', 'actor'], ['actor', 'reviewer'], ['reviewer', 'rules'], ['rules', 'payment'], ['reviewer', 'evaluator'], ['rules', 'evaluator'], ['payment', 'evaluator']],
  };
  const CONFIG_COMPONENTS = {
    none: { reviewer: false, rules: false },
    rules: { reviewer: false, rules: true },
    reviewer: { reviewer: true, rules: false },
    both: { reviewer: true, rules: true },
  };
  const ALL_EDGES = [
    ['request', 'actor'], ['actor', 'reviewer'], ['actor', 'rules'], ['actor', 'payment'], ['actor', 'evaluator'],
    ['reviewer', 'rules'], ['reviewer', 'payment'], ['reviewer', 'evaluator'],
    ['rules', 'payment'], ['rules', 'evaluator'], ['payment', 'evaluator'],
  ];
  const EDGE_LABEL = {
    'actor>evaluator': 'no refund proposed',
    'reviewer>evaluator': 'block / escalate',
    'rules>evaluator': 'rule stop',
  };

  /* Layouts: node centers and explicit cubic control points per edge.   */
  const LAYOUTS = {
    wide: {
      viewBox: [0, 0, 1080, 500],
      r: 17,
      nodes: {
        msg: [72, 172], rec: [72, 338], request: [168, 255], actor: [305, 255],
        reviewer: [492, 142], rules: [640, 382], payment: [800, 255], evaluator: [968, 255],
      },
      labelAbove: ['msg'],
      edges: {
        'request>actor': null,
        'actor>reviewer': [[365, 200], [415, 145]],
        'actor>rules': [[405, 330], [525, 385]],
        'actor>payment': null,
        'actor>evaluator': [[335, 18], [935, 18]],
        'reviewer>rules': [[548, 230], [600, 320]],
        'reviewer>payment': [[640, 142], [722, 196]],
        'reviewer>evaluator': [[640, 90], [905, 110]],
        'rules>payment': [[722, 382], [772, 318]],
        'rules>evaluator': [[800, 448], [948, 410]],
        'payment>evaluator': null,
      },
      edgeLabels: {
        'actor>evaluator': [636, 46],
        'reviewer>evaluator': [770, 92],
        'rules>evaluator': [870, 446],
      },
      dataRef: { path: [[72, 338], [220, 452], [520, 462], [640, 382]], label: [350, 452] },
      ports: { msg: [[72, 172], [168, 255]], rec: [[72, 338], [168, 255]] },
    },
    tall: {
      viewBox: [0, 0, 420, 900],
      r: 17,
      nodes: {
        msg: [112, 104], rec: [308, 104], request: [210, 172], actor: [210, 262],
        reviewer: [96, 392], rules: [324, 526], payment: [210, 664], evaluator: [210, 806],
      },
      labelAbove: ['msg', 'rec'],
      labelSide: { actor: 'left', payment: 'left' },
      edges: {
        'request>actor': null,
        'actor>reviewer': [[170, 316], [110, 340]],
        'actor>rules': [[262, 340], [326, 440]],
        'actor>payment': null,
        'actor>evaluator': [[414, 340], [414, 760]],
        'reviewer>rules': [[176, 432], [262, 486]],
        'reviewer>payment': [[96, 500], [150, 610]],
        'reviewer>evaluator': [[8, 540], [28, 790]],
        'rules>payment': [[324, 606], [268, 640]],
        'rules>evaluator': [[332, 660], [300, 770]],
        'payment>evaluator': null,
      },
      edgeLabels: {
        'actor>evaluator': [366, 690],
        'reviewer>evaluator': [44, 690],
        'rules>evaluator': [354, 600],
      },
      dataRef: { path: [[308, 104], [400, 190], [396, 400], [324, 526]], label: [305, 236] },
      ports: { msg: [[112, 104], [210, 172]], rec: [[308, 104], [210, 172]] },
    },
  };

  // Fit a base viewBox into the container without upscaling beyond maxScale,
  // so nodes stay compact and extra space becomes whitespace.
  function fitViewBox(svg, container, base, maxScale) {
    const cw = container.clientWidth, ch = container.clientHeight;
    const [bx, by, bw, bh] = base;
    if (!cw || !ch) { svg.setAttribute('viewBox', base.join(' ')); return; }
    const k = Math.min(cw / bw, ch / bh, maxScale);
    const vw = cw / k, vh = ch / k;
    svg.setAttribute('viewBox', [bx - (vw - bw) / 2, by - (vh - bh) / 2, vw, vh].map(v => fmt(v, 2)).join(' '));
  }

  function edgeKey(a, b) { return a + '>' + b; }

  function trimToward(p, q, d) {
    const dx = q[0] - p[0], dy = q[1] - p[1], L = Math.hypot(dx, dy) || 1;
    return [p[0] + dx / L * d, p[1] + dy / L * d];
  }

  function edgeGeometry(layout, a, b) {
    const pa = layout.nodes[a], pb = layout.nodes[b];
    const cps = layout.edges[edgeKey(a, b)];
    const ra = a === 'request' ? 5 : layout.r + 3, rb = layout.r + 7;
    if (!cps) {
      const p0 = trimToward(pa, pb, ra), p1 = trimToward(pb, pa, rb);
      return `M${fmt(p0[0])} ${fmt(p0[1])} L${fmt(p1[0])} ${fmt(p1[1])}`;
    }
    const p0 = trimToward(pa, cps[0], ra), p1 = trimToward(pb, cps[1], rb);
    return `M${fmt(p0[0])} ${fmt(p0[1])} C${cps[0][0]} ${cps[0][1]} ${cps[1][0]} ${cps[1][1]} ${fmt(p1[0])} ${fmt(p1[1])}`;
  }

  /* ------------------------------------------------------------------ */
  /* Glyph definitions (mirrored in assets/glyphs.svg)                   */
  /* ------------------------------------------------------------------ */

  function addDefs(svg, prefix) {
    const defs = s('defs', null, svg);
    const mk = (id, cls) => {
      const m = s('marker', { id: prefix + id, viewBox: '0 0 8 8', refX: 6.5, refY: 4, markerWidth: 7, markerHeight: 7, orient: 'auto-start-reverse', markerUnits: 'userSpaceOnUse' }, defs);
      s('path', { d: 'M1 1 L7 4 L1 7', class: 'arrow ' + cls }, m);
    };
    mk('arrow-struct', 'arrow-struct');
    mk('arrow-ok', 'arrow-ok');
    mk('arrow-warn', 'arrow-warn');
    mk('arrow-bad', 'arrow-bad');
    mk('arrow-model', 'arrow-model');
    mk('arrow-calc', 'arrow-calc');
    const sym = (id, d) => { const g = s('symbol', { id: prefix + id, viewBox: '-6 -6 12 12', overflow: 'visible' }, defs); s('path', { d }, g); };
    sym('g-check', 'M-3.2 0.2 L-1 2.4 L3.3 -2.4');
    sym('g-stop', 'M-3 0 H3');
    sym('g-up', 'M0 3.4 V-3 M-2.8 -0.4 L0 -3.2 L2.8 -0.4');
    sym('g-bang', 'M0 -3.4 V0.8 M0 3 V3.1');
    sym('g-dot', 'M0 0 h0.01');
    return defs;
  }

  function stateGlyph(state) {
    switch (state) {
      case 'completed': return 'g-check';
      case 'blocked': return 'g-stop';
      case 'escalated': return 'g-up';
      case 'error': case 'unsafe': return 'g-bang';
      case 'declined': return 'g-stop';
      default: return null;
    }
  }

  /* ------------------------------------------------------------------ */
  /* Text helpers for node status lines                                  */
  /* ------------------------------------------------------------------ */

  function money(c) {
    if (c === null || c === undefined) return 'Unavailable';
    return '$' + (c / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  const RULE_LABEL = {
    ownership: 'ownership', return_window: 'return window', duplicate_or_excess_refund: 'duplicate / excess',
    human_approval_required: 'approval limit',
  };

  // Display state for a completed event, including the derived 'unsafe'.
  function displayState(ev, trace) {
    if (ev.node === 'payment' && ev.state === 'completed' && trace.outcome && trace.outcome.unauthorized === true) return 'unsafe';
    if (ev.node === 'actor' && ev.output) {
      if (ev.output.action === 'escalate') return 'escalated';
      if (ev.output.action === 'decline') return 'declined';
    }
    return ev.state;
  }

  function nodeStatus(ev, trace) {
    const o = ev.output || {};
    switch (ev.node) {
      case 'request': return 'Received';
      case 'actor':
        if (o.action === 'refund') return 'Proposes ' + money(o.amount_cents);
        if (o.action === 'escalate') return 'Escalates';
        if (o.action === 'decline') return 'Declines';
        return ev.state;
      case 'reviewer':
        return o.verdict === 'approve' ? 'Approves' : o.verdict === 'block' ? 'Blocks' : o.verdict === 'escalate' ? 'Escalates' : ev.state;
      case 'rules':
        if (o.allowed) return 'Allows';
        return 'Stops · ' + (o.rules || []).map(r => RULE_LABEL[r] || r).join(', ');
      case 'payment':
        if (ev.state === 'error') return 'Error · unresolved';
        if (trace.outcome && trace.outcome.unauthorized) return 'Pays ' + money(o.delta_cents) + ' · unauthorized';
        return 'Pays ' + money(o.delta_cents);
      case 'evaluator': {
        if (o.evaluated === false || ev.state === 'error') return 'Unresolved';
        if (o.exposure_cents > 0) return 'Exposure ' + money(o.exposure_cents);
        return 'No exposure';
      }
      default: return ev.state;
    }
  }

  // Short label for what travels along an executed edge, taken from the
  // saved output of the source event. Nothing is invented.
  function payloadLabel(src, trace) {
    if (!src) return '';
    const o = src.output || {};
    switch (src.node) {
      case 'request': return 'request + trusted order';
      case 'actor': return o.action === 'refund' ? 'proposal · refund ' + money(o.amount_cents) : o.action === 'escalate' ? 'proposal · escalate' : o.action === 'decline' ? 'proposal · decline' : 'proposal';
      case 'reviewer': return 'verdict · ' + (o.verdict || src.state);
      case 'rules': return o.allowed ? 'rules · allowed' : 'rules · stop';
      case 'payment': return src.state === 'error' ? 'error · unresolved' : 'ledger ' + (o.delta_cents >= 0 ? '+' : '') + money(o.delta_cents);
      default: return '';
    }
  }

  // One plain sentence describing a saved event, for the step caption.
  function narrate(ev, trace) {
    const o = ev.output || {}, i = ev.input || {};
    switch (ev.node) {
      case 'request': return `Request arrives: an untrusted customer message and the trusted order record (${money(o.requested_cents)} requested).`;
      case 'actor':
        if (o.action === 'refund') return `Refund agent proposes a ${money(o.amount_cents)} refund. This is a saved proposal, not a payment.`;
        if (o.action === 'escalate') return 'Refund agent escalates instead of proposing a refund, so no payment is requested.';
        if (o.action === 'decline') return 'Refund agent declines the request, so no payment is requested.';
        return 'Refund agent records its proposal.';
      case 'reviewer':
        if (o.verdict === 'approve') return 'Reviewer approves the saved proposal. It passes on unchanged.';
        if (o.verdict === 'block') return 'Reviewer blocks the proposal. Every route to payment is skipped.';
        if (o.verdict === 'escalate') return 'Reviewer escalates to human review. Payment is skipped.';
        return 'Reviewer records a verdict.';
      case 'rules':
        if (o.allowed) return 'Policy rules check the proposal against the trusted record: allowed.';
        return 'Policy rules stop the payment: ' + (o.rules || []).map(r => RULE_LABEL[r] || r).join(', ') + '. Checks use the trusted record, not the message.';
      case 'payment':
        if (ev.state === 'error') return 'Simulated payment times out before commit. The outcome is unresolved.';
        if (trace.outcome && trace.outcome.unauthorized) return `Simulated payment executes ${money(o.delta_cents)}. The trusted record does not authorize it.`;
        return `Simulated payment executes ${money(o.delta_cents)}.`;
      case 'evaluator':
        if (o.evaluated === false || ev.state === 'error') return 'Evaluator cannot score an unresolved payment. Exposure is unavailable, not zero.';
        if (o.exposure_cents > 0) return `Evaluator compares the ledger change with trusted policy: ${money(o.exposure_cents)} unauthorized exposure.`;
        return `Evaluator compares the ledger change with trusted policy: no unauthorized exposure (ledger change ${money(i.ledger_delta_cents)}).`;
      default: return '';
    }
  }

  /* ------------------------------------------------------------------ */
  /* Workflow topology                                                   */
  /* ------------------------------------------------------------------ */

  function mountTopology(container, callbacks) {
    callbacks = callbacks || {};
    let layoutName = 'wide';
    let trace = null, caseRecord = null, config = 'none';
    let playback = { eventIndex: Infinity, progress: 1, playing: false, reducedMotion: false };
    let selected = null;
    const svg = s('svg', { class: 'topology', role: 'group', 'aria-label': 'Request topology' }, container);
    const title = s('title', { text: 'Request topology: executed path from saved structured events' }, svg);
    const prefix = 'rgw-';
    addDefs(svg, prefix);
    const gStruct = s('g', { class: 'layer-struct' }, svg);
    const gExec = s('g', { class: 'layer-exec' }, svg);
    const gLabels = s('g', { class: 'layer-edge-labels' }, svg);
    const gNodes = s('g', { class: 'layer-nodes' }, svg);
    const gGates = s('g', { class: 'layer-gates' }, svg);
    const gFx = s('g', { class: 'layer-fx' }, svg);
    const packet = s('circle', { class: 'packet', r: 5, cx: -20, cy: -20 }, svg);
    const tag = s('g', { class: 'packet-tag' }, svg);
    const tagBg = s('rect', { class: 'packet-tag-bg', rx: 4, height: 17 }, tag);
    const tagText = s('text', { class: 'packet-tag-text', y: 12 }, tag);
    let nodeEls = {}, execPaths = {}, gates = {}, prevDone = {}, popUntil = {}, lastTrace = null;

    function chooseLayout() {
      const w = container.clientWidth, h = container.clientHeight;
      const next = (w < 640 || w / Math.max(h, 1) < 0.95) ? 'tall' : 'wide';
      if (next !== layoutName || !built) { layoutName = next; build(); render(); }
      fitViewBox(svg, container, LAYOUTS[layoutName].viewBox, 1.15);
    }
    let built = false;

    function build() {
      const L = LAYOUTS[layoutName];
      built = true;
      svg.setAttribute('class', 'topology layout-' + layoutName);
      clear(gStruct); clear(gExec); clear(gLabels); clear(gNodes); clear(gGates); clear(gFx);
      nodeEls = {}; execPaths = {}; gates = {};

      // Data reference: trusted record -> rules (static, not a call).
      const dp = L.dataRef.path;
      const dEnd = trimToward(dp[3], dp[2], L.r + 6);
      s('path', { id: 'ref-rec-rules', class: 'edge dataref', d: `M${dp[0][0]} ${dp[0][1]} C${dp[1][0]} ${dp[1][1]} ${dp[2][0]} ${dp[2][1]} ${fmt(dEnd[0])} ${fmt(dEnd[1])}` }, gStruct);
      s('text', { id: 'ref-rec-rules-label', class: 'edge-label dataref-label', x: L.dataRef.label[0], y: L.dataRef.label[1], 'text-anchor': 'middle', text: 'trusted record (data reference)' }, gLabels);

      // Port stubs: the two visual inputs feed the single request event.
      for (const p of ['msg', 'rec']) {
        const [a, b] = L.ports[p];
        const a2 = trimToward(a, b, 15), b2 = trimToward(b, a, 4);
        s('path', { id: 'port-' + p, class: 'edge port port-' + p, d: `M${fmt(a2[0])} ${fmt(a2[1])} L${fmt(b2[0])} ${fmt(b2[1])}` }, gStruct);
      }

      for (const [a, b] of ALL_EDGES) {
        const k = edgeKey(a, b), d = edgeGeometry(L, a, b);
        s('path', { id: 'struct-' + a + '-' + b, class: 'edge struct', d, 'data-edge': k, 'marker-end': `url(#${prefix}arrow-struct)` }, gStruct);
        execPaths[k] = s('path', { id: 'exec-' + a + '-' + b, class: 'edge exec', d, 'data-edge': k }, gExec);
        // "Route not taken" mark, shown on a permitted route the saved trace skipped.
        const sp = gStruct.lastChild, len = sp.getTotalLength ? sp.getTotalLength() : 0;
        const mid = len ? sp.getPointAtLength(len * (b === 'evaluator' && a !== 'payment' ? 0.32 : 0.5)) : { x: 0, y: 0 };
        const gate = s('g', { class: 'gate', transform: `translate(${fmt(mid.x)} ${fmt(mid.y)})`, 'data-edge': k }, gGates);
        s('title', { text: 'Route not taken in this saved trace' }, gate);
        s('circle', { class: 'gate-bg', r: 7 }, gate);
        s('path', { class: 'gate-x', d: 'M-3 -3 L3 3 M3 -3 L-3 3' }, gate);
        gates[k] = gate;
        if (EDGE_LABEL[k]) {
          const [x, y] = L.edgeLabels[k];
          s('text', { class: 'edge-label', x, y, 'text-anchor': 'middle', 'data-edge': k, text: EDGE_LABEL[k] }, gLabels);
        }
      }

      for (const n of VISUAL_NODES) {
        const [x, y] = L.nodes[n.id];
        if (n.kind === 'hub') {
          const g = s('g', { class: 'node hub', 'data-node': n.id, transform: `translate(${x} ${y})`, 'aria-hidden': 'true' }, gNodes);
          s('circle', { class: 'hub-dot', r: 4.5 }, g);
          nodeEls[n.id] = { g };
          continue;
        }
        const g = s('g', { class: 'node kind-' + n.kind, id: 'node-' + n.id, 'data-node': n.id, 'data-canonical': n.canonical, transform: `translate(${x} ${y})`, tabindex: 0, role: 'button' }, gNodes);
        s('circle', { class: 'hit', r: 30 }, g);
        s('circle', { class: 'focus-ring', r: 27 }, g);
        s('circle', { class: 'sel-ring', r: 24 }, g);
        s('circle', { class: 'run-ring', r: 22 }, g);
        const r = L.r;
        if (n.kind === 'agent') {
          s('circle', { class: 'shape', r }, g);
          s('circle', { class: 'kind-mark', r: 4.2 }, g);
        } else if (n.kind === 'input-untrusted' || n.kind === 'input-trusted') {
          s('path', { class: 'shape', d: `M0 ${-r - 2} L${r + 2} 0 L0 ${r + 2} L${-r - 2} 0 Z` }, g);
          if (n.kind === 'input-untrusted') s('text', { class: 'kind-text', y: 4.5, 'text-anchor': 'middle', text: '?' }, g);
          else s('path', { class: 'kind-line', d: 'M-5 -3 H5 M-5 0.5 H5 M-5 4 H5' }, g);
        } else {
          s('rect', { class: 'shape', x: -r, y: -r, width: 2 * r, height: 2 * r, rx: 5 }, g);
          const glyph = n.kind === 'tool' ? '$' : n.kind === 'eval' ? 'Δ' : '§';
          s('text', { class: 'kind-text', y: 5, 'text-anchor': 'middle', text: glyph }, g);
        }
        const badge = s('g', { class: 'badge', transform: `translate(${r - 2} ${-r + 2})` }, g);
        s('circle', { class: 'badge-bg', r: 7.5 }, badge);
        const use = s('use', { class: 'badge-glyph', href: '#' + prefix + 'g-check', x: -6, y: -6, width: 12, height: 12 }, badge);
        const above = (L.labelAbove || []).includes(n.id);
        const side = (L.labelSide || {})[n.id];
        const ly = side ? -2 : above ? -r - 26 : r + 18;
        const lx = side === 'left' ? -r - 12 : side === 'right' ? r + 12 : 0;
        const anchor = side === 'left' ? 'end' : side === 'right' ? 'start' : 'middle';
        const label = s('text', { class: 'node-label', x: lx, y: ly, 'text-anchor': anchor, text: n.label }, g);
        const status = s('text', { class: 'node-status', x: lx, y: ly + 15, 'text-anchor': anchor, text: '' }, g);
        const tagY = above ? ly - 17 : ly + 31;
        if (n.kind === 'input-untrusted') s('text', { class: 'node-tag tag-untrusted', x: 0, y: tagY, 'text-anchor': 'middle', text: 'UNTRUSTED' }, g);
        if (n.kind === 'input-trusted') s('text', { class: 'node-tag tag-trusted', x: 0, y: tagY, 'text-anchor': 'middle', text: 'TRUSTED' }, g);
        g.addEventListener('click', () => activate(n.id));
        g.addEventListener('keydown', e => {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); activate(n.id); }
          else if (['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp'].includes(e.key)) { e.preventDefault(); moveFocus(n.id, e.key); }
        });
        nodeEls[n.id] = { g, use, label, status };
      }
    }

    const FOCUS_ORDER = ['msg', 'rec', 'actor', 'reviewer', 'rules', 'payment', 'evaluator'];
    function moveFocus(id, key) {
      const i = FOCUS_ORDER.indexOf(id);
      const d = (key === 'ArrowRight' || key === 'ArrowDown') ? 1 : -1;
      const next = FOCUS_ORDER[(i + d + FOCUS_ORDER.length) % FOCUS_ORDER.length];
      nodeEls[next] && nodeEls[next].g.focus();
    }

    function activate(id) {
      selected = id;
      render();
      if (callbacks.onNodeSelect) {
        const ev = trace ? trace.events.find(e => e.node === VN[id].canonical) || null : null;
        callbacks.onNodeSelect(id, VN[id].canonical, ev);
      }
    }

    function render() {
      if (!trace) return;
      const comps = CONFIG_COMPONENTS[config] || {};
      const allowed = new Set((CONFIG_EDGES[config] || []).map(e => edgeKey(e[0], e[1])));
      const events = trace.events;
      const ei = Math.min(playback.eventIndex, events.length);
      const prog = playback.progress;
      const rm = !!playback.reducedMotion;

      // Structural edges.
      gStruct.querySelectorAll('.struct').forEach(p => {
        p.classList.toggle('in-config', allowed.has(p.dataset.edge));
      });
      gLabels.querySelectorAll('.edge-label[data-edge]').forEach(t => t.classList.toggle('in-config', allowed.has(t.dataset.edge)));
      const rulesInConfig = !!comps.rules;
      svg.querySelector('#ref-rec-rules').classList.toggle('in-config', rulesInConfig);
      svg.querySelector('#ref-rec-rules-label').classList.toggle('in-config', rulesInConfig);

      // Executed edges: built ONLY from events[i].from -> events[i].node.
      for (const k of Object.keys(execPaths)) execPaths[k].setAttribute('class', 'edge exec');
      let packetEdge = null;
      events.forEach((ev, i) => {
        if (!ev.from) return;
        const k = edgeKey(ev.from, ev.node), p = execPaths[k];
        if (!p) return;
        const src = events.find(x => x.node === ev.from);
        const srcState = src ? displayState(src, trace) : 'completed';
        let tone = 'ok';
        if (srcState === 'blocked' || srcState === 'escalated' || srcState === 'declined') tone = 'warn';
        if (srcState === 'error') tone = 'bad';
        if (ev.node === 'payment' && trace.outcome && trace.outcome.unauthorized === true) tone = 'bad';
        let phase = 'future';
        if (i < ei) phase = 'done';
        else if (i === ei && !rm) phase = prog >= 0.5 ? 'done' : 'active';
        else if (i === ei && rm) phase = 'future';
        p.setAttribute('class', `edge exec tone-${tone} phase-${phase}`);
        p.setAttribute('marker-end', phase === 'done' ? `url(#${prefix}arrow-${tone})` : '');
        if (phase === 'active') {
          const len = p.getTotalLength(), t = Math.max(0, Math.min(1, prog / 0.5));
          p.setAttribute('stroke-dasharray', `${fmt(len * t, 2)} ${fmt(len + 2, 2)}`);
        } else p.removeAttribute('stroke-dasharray');
        if (phase === 'active' && playback.playing) packetEdge = { p, t: prog / 0.5, tone, label: payloadLabel(src, trace) };
      });

      // Ports animate with the request event.
      const reqDone = ei > 0 || (ei === 0 && (prog >= 0.5 && !rm));
      ['msg', 'rec'].forEach(p => {
        const el = svg.querySelector('#port-' + p);
        el.classList.toggle('active', reqDone);
      });

      // Packet.
      if (packetEdge && !rm) {
        const len = packetEdge.p.getTotalLength();
        const pt = packetEdge.p.getPointAtLength(len * Math.max(0, Math.min(1, packetEdge.t)));
        packet.setAttribute('cx', fmt(pt.x, 2)); packet.setAttribute('cy', fmt(pt.y, 2));
        packet.setAttribute('class', 'packet visible tone-' + packetEdge.tone);
        if (tagText.textContent !== packetEdge.label) {
          tagText.textContent = packetEdge.label;
          const w = (tagText.getComputedTextLength ? tagText.getComputedTextLength() : packetEdge.label.length * 6) + 12;
          tagBg.setAttribute('width', fmt(w)); tagBg.setAttribute('x', fmt(-w / 2)); tagText.setAttribute('x', 0);
          tagText.setAttribute('text-anchor', 'middle');
        }
        tag.setAttribute('transform', `translate(${fmt(pt.x, 2)} ${fmt(pt.y - 28, 2)})`);
        tag.setAttribute('class', 'packet-tag visible tone-' + packetEdge.tone);
      } else {
        packet.setAttribute('class', 'packet');
        tag.setAttribute('class', 'packet-tag');
      }

      // Routes not taken: after a node with alternatives completes, mark the
      // permitted outgoing routes the saved trace did not use.
      const executed = new Set(events.filter(e => e.from).map(e => edgeKey(e.from, e.node)));
      for (const k of Object.keys(gates)) {
        const [a] = k.split('>');
        const ai = events.findIndex(e => e.node === a);
        const decided = ai >= 0 && (ai < ei || (ai === ei && !playback.playing && prog >= 1));
        const show = allowed.has(k) && !executed.has(k) && decided;
        gates[k].setAttribute('class', 'gate' + (show ? ' shown' : ''));
      }

      // Nodes.
      const nowDone = {};
      for (const n of VISUAL_NODES) {
        const el = nodeEls[n.id]; if (!el) continue;
        if (n.kind === 'hub') { el.g.setAttribute('class', 'node hub' + (reqDone ? ' active' : '')); continue; }
        const idx = events.findIndex(e => e.node === n.canonical);
        const ev = idx >= 0 ? events[idx] : null;
        let cls = 'node kind-' + n.kind, status = '', glyph = null, aria;
        const inConfig = n.id === 'reviewer' ? !!comps.reviewer : n.id === 'rules' ? !!comps.rules : true;
        if (!inConfig) {
          cls += ' st-off'; status = 'Not in this setup';
        } else if (!ev) {
          cls += ' st-skipped'; status = 'Not run';
        } else {
          let phase;
          if (idx < ei) phase = 'done';
          else if (idx === ei) phase = (rm ? 'pending' : (prog >= 0.5 ? 'running' : 'pending'));
          else phase = 'pending';
          if (idx === ei && playback.playing && !rm && prog >= 0.5) phase = 'running';
          if (idx === ei && !playback.playing && prog >= 1) phase = 'done';
          if (phase === 'done') {
            const st = displayState(ev, trace);
            cls += ' st-' + st; glyph = stateGlyph(st);
            if (lastTrace === trace && prevDone[n.id] === false && !rm) {
              popUntil[n.id] = performance.now() + 650;
              if (n.id === 'payment') floatDelta(n.id, ev);
            }
            if ((popUntil[n.id] || 0) > performance.now()) cls += ' pop';
            nowDone[n.id] = true;
            status = n.id === 'msg' ? 'Received' : n.id === 'rec' ? 'Loaded' : nodeStatus(ev, trace);
          } else if (phase === 'running') { cls += ' st-running'; status = 'Running'; }
          else { cls += ' st-pending'; status = 'Pending'; }
        }
        if (selected === n.id) cls += ' selected';
        el.g.setAttribute('class', cls);
        el.status.textContent = status;
        if (glyph) { el.use.setAttribute('href', '#' + prefix + glyph); }
        aria = `${n.label}, ${n.role}. ${status}. Inspect saved evidence.`;
        el.g.setAttribute('aria-label', aria);
        el.g.setAttribute('aria-pressed', selected === n.id ? 'true' : 'false');
      }
      for (const n of VISUAL_NODES) prevDone[n.id] = !!nowDone[n.id];
      lastTrace = trace;
    }

    // Brief "+$X" rising from the payment node when the ledger changes.
    function floatDelta(id, ev) {
      const L = LAYOUTS[layoutName], [x, y] = L.nodes[id];
      const o = ev.output || {};
      const unsafe = trace.outcome && trace.outcome.unauthorized === true;
      const text = ev.state === 'error' ? 'timeout' : 'ledger ' + (o.delta_cents >= 0 ? '+' : '') + money(o.delta_cents);
      const t = s('text', { class: 'float-delta ' + (ev.state === 'error' || unsafe ? 'tone-bad' : 'tone-ok'), x, y: y - L.r - 14, 'text-anchor': 'middle', text }, gFx);
      setTimeout(() => t.remove(), 1700);
    }

    const ro = new ResizeObserver(() => chooseLayout());
    ro.observe(container);
    build();

    return {
      setTrace(t, rec, cfg) { if (t !== trace) prevDone = {}; trace = t; caseRecord = rec; config = cfg; render(); },
      setPlayback(pb) { playback = Object.assign({}, playback, pb); render(); },
      selectNode(id) { selected = id; render(); },
      focusNode(id) { nodeEls[id] && nodeEls[id].g && nodeEls[id].g.focus(); },
      get layout() { return layoutName; },
      svg,
    };
  }

  /* ------------------------------------------------------------------ */
  /* Small topology thumbnail for one trace                              */
  /* ------------------------------------------------------------------ */

  function renderPathThumb(svg, trace, config) {
    clear(svg);
    const L = LAYOUTS.wide;
    svg.setAttribute('viewBox', '30 70 990 370');
    svg.setAttribute('class', 'thumb');
    svg.setAttribute('aria-hidden', 'true');
    const comps = CONFIG_COMPONENTS[config] || {};
    const allowed = CONFIG_EDGES[config] || [];
    for (const [a, b] of allowed) s('path', { class: 'tedge struct', d: edgeGeometry(L, a, b) }, svg);
    for (const ev of trace.events) {
      if (!ev.from) continue;
      const src = trace.events.find(x => x.node === ev.from);
      const st = src ? displayState(src, trace) : 'completed';
      let tone = (st === 'blocked' || st === 'escalated' || st === 'declined') ? 'warn' : st === 'error' ? 'bad' : 'ok';
      if (ev.node === 'payment' && trace.outcome.unauthorized === true) tone = 'bad';
      s('path', { class: 'tedge exec tone-' + tone, d: edgeGeometry(L, ev.from, ev.node) }, svg);
    }
    for (const id of ['actor', 'reviewer', 'rules', 'payment', 'evaluator', 'request']) {
      const [x, y] = L.nodes[id];
      const ev = trace.events.find(e => e.node === id);
      const inConfig = id === 'reviewer' ? !!comps.reviewer : id === 'rules' ? !!comps.rules : true;
      const st = !inConfig ? 'off' : !ev ? 'skipped' : displayState(ev, trace);
      const kind = VN[id].kind;
      const cls = 'tnode st-' + st;
      if (kind === 'agent') s('circle', { class: cls, cx: x, cy: y, r: 26 }, svg);
      else if (kind === 'hub') s('circle', { class: cls, cx: x, cy: y, r: 12 }, svg);
      else s('rect', { class: cls, x: x - 24, y: y - 24, width: 48, height: 48, rx: 8 }, svg);
    }
    return svg;
  }

  /* ------------------------------------------------------------------ */
  /* Density chart (prior dashed, posterior solid, credible band)        */
  /* ------------------------------------------------------------------ */

  function renderDensity(svg, cell, density, animate) {
    clear(svg);
    const W = 300, H = 150, l = 30, r = 8, t = 10, b = 26;
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.setAttribute('class', 'density');
    svg.setAttribute('role', 'img');
    const max = Math.max(...density.prior, ...density.posterior) * 1.08 || 1;
    const X = p => l + p * (W - l - r), Y = v => (H - b) - v / max * (H - b - t);
    s('title', { text: `Prior and posterior densities over probability 0 to 1. Posterior Beta(${cell.posterior_a}, ${cell.posterior_b}).` }, svg);
    if (cell.credible95) {
      s('rect', { class: 'ci-band', x: fmt(X(cell.credible95[0]), 2), y: t, width: fmt(X(cell.credible95[1]) - X(cell.credible95[0]), 2), height: H - b - t }, svg);
    }
    for (const p of [0, 0.25, 0.5, 0.75, 1]) {
      s('line', { class: 'grid', x1: X(p), x2: X(p), y1: t, y2: H - b }, svg);
      s('text', { class: 'axis-text', x: X(p), y: H - b + 13, 'text-anchor': 'middle', text: p === 0 ? '0' : p === 1 ? '1' : String(p) }, svg);
    }
    s('line', { class: 'axis', x1: l, x2: W - r, y1: H - b, y2: H - b }, svg);
    s('text', { class: 'axis-text', x: (l + W - r) / 2, y: H - 2, 'text-anchor': 'middle', text: 'unauthorized-payment probability p' }, svg);
    s('text', { class: 'axis-text', x: l - 4, y: t + 4, 'text-anchor': 'end', text: fmt(max, 1) }, svg);
    s('text', { class: 'axis-text', x: l - 4, y: H - b, 'text-anchor': 'end', text: '0' }, svg);
    const path = vals => density.x.map((p, i) => `${i ? 'L' : 'M'}${fmt(X(p), 2)} ${fmt(Y(vals[i]), 2)}`).join(' ');
    s('path', { class: 'prior-line', d: path(density.prior) }, svg);
    const post = s('path', { class: 'posterior-line', d: path(density.posterior) }, svg);
    // Optional update animation: the curve morphs from the prior into the
    // saved posterior, then the credible band fades in. Shape only; the
    // end state is exactly the saved posterior density.
    if (animate) {
      const band = svg.querySelector('.ci-band');
      if (band) band.setAttribute('class', 'ci-band reveal');
      const t0 = performance.now(), dur = 1100;
      const step = now => {
        if (!svg.isConnected) return;
        const u = Math.min(1, (now - t0) / dur), e = u < .5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;
        post.setAttribute('d', path(density.prior.map((v, i) => v + (density.posterior[i] - v) * e)));
        if (u < 1) requestAnimationFrame(step);
      };
      post.setAttribute('d', path(density.prior));
      requestAnimationFrame(step);
    }
    return svg;
  }

  /* ------------------------------------------------------------------ */
  /* Compact interval comparison across the four setups                  */
  /* ------------------------------------------------------------------ */

  function renderIntervals(svg, projections, opts) {
    clear(svg);
    const order = opts.order, labels = opts.labels;
    const W = 300, rowH = 26, top = 6, l = 92, r = 12, H = top + order.length * rowH + 22;
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.setAttribute('class', 'intervals');
    svg.setAttribute('role', 'img');
    const X = p => l + p * (W - l - r);
    const desc = order.map(c => {
      const q = projections[c];
      return `${labels[c]}: mean ${(100 * q.posterior_mean).toFixed(1)}%, 95% credible ${(100 * q.credible95[0]).toFixed(1)} to ${(100 * q.credible95[1]).toFixed(1)}%` + (q.exact_upper == null ? ', exact upper unavailable' : `, exact upper ${(100 * q.exact_upper).toFixed(1)}%`);
    }).join('; ');
    s('title', { text: 'Weighted projection by setup. ' + desc }, svg);
    for (const p of [0, 0.25, 0.5, 0.75, 1]) {
      s('line', { class: 'grid', x1: X(p), x2: X(p), y1: top - 2, y2: top + order.length * rowH }, svg);
      s('text', { class: 'axis-text', x: X(p), y: top + order.length * rowH + 13, 'text-anchor': 'middle', text: Math.round(p * 100) + '%' }, svg);
    }
    order.forEach((c, i) => {
      const q = projections[c], y = top + i * rowH + rowH / 2;
      const g = s('g', { class: 'irow' + (c === opts.selected ? ' selected' : '') }, svg);
      s('text', { class: 'irow-label', x: 0, y: y + 4, text: labels[c] }, g);
      s('line', { class: 'ci', x1: X(q.credible95[0]), x2: X(q.credible95[1]), y1: y, y2: y }, g);
      s('circle', { class: 'mean', cx: X(q.posterior_mean), cy: y, r: 3.6 }, g);
      if (q.exact_upper != null) s('path', { class: 'upper', d: `M${fmt(X(q.exact_upper))} ${y - 6} V${y + 6}` }, g);
    });
    return svg;
  }

  /* ------------------------------------------------------------------ */
  /* Probabilistic risk model topology                                   */
  /* ------------------------------------------------------------------ */

  const MODEL_LAYOUTS = {
    wide: {
      viewBox: [0, 0, 1000, 560],
      rows: i => 96 + i * 74,
      x: { prior: 96, bus: 182, p: 268, y: 400, calcBus: 486, post: 572, w: 726, sum: 892 },
      prior: [96, 300], sum: [892, 300],
      headers: [[96, 'Prior'], [268, 'Scenario risk'], [400, 'Observed'], [572, 'Posterior'], [726, 'Assumed mix'], [892, 'Projection']],
      headerSub: [[96, 'a, b (fixed)'], [268, 'p[s, m]'], [400, 'Y[i, s, m]'], [572, 'calculated'], [726, 'w[s] (assumption)'], [892, 'Σ w[s] p[s, m]']],
      plate: [362, 64, 76, 452],
      nameX: 210,
      postW: 128,
    },
    tall: {
      viewBox: [0, 0, 420, 1000],
      rows: i => 190 + i * 118,
      x: { prior: 64, bus: 24, p: 64, y: 168, calcBus: 232, post: 300, w: 300, sum: 210 },
      prior: [64, 74], sum: [210, 920],
      headers: [],
      headerSub: [],
      plate: [134, 140, 68, 712],
      nameX: 48,
      postW: 116,
    },
  };

  function mountModel(container, callbacks) {
    callbacks = callbacks || {};
    let layoutName = 'wide';
    let analysis = null, opts = {}, stage = null;
    const svg = s('svg', { class: 'model', role: 'group', 'aria-label': 'Probabilistic risk model' }, container);
    const prefix = 'rgm-';

    function chooseLayout() {
      const w = container.clientWidth;
      const next = w < 640 ? 'tall' : 'wide';
      if (next !== layoutName || !mbuilt) { layoutName = next; render(); }
      fitViewBox(svg, container, MODEL_LAYOUTS[layoutName].viewBox, 1.2);
    }
    let mbuilt = false;

    function render() {
      clear(svg);
      const L = MODEL_LAYOUTS[layoutName];
      mbuilt = true;
      fitViewBox(svg, container, L.viewBox, 1.2);
      svg.setAttribute('class', 'model layout-' + layoutName + (stage === null ? '' : ' walk walk-s' + stage));
      s('title', { text: 'Probabilistic risk model: prior, scenario probabilities, observed outcomes, calculated posteriors, assumed weights and weighted projection. Separate from the agent workflow.' }, svg);
      addDefs(svg, prefix);
      if (!analysis) return;
      const order = opts.scenarioOrder, labels = opts.labels, cfg = opts.configuration;
      const cells = analysis.cells[cfg];
      const proj = analysis.projections[cfg];
      const weights = analysis.weights || opts.weights;
      const tall = layoutName === 'tall';
      const gEdges = s('g', { class: 'm-edges' }, svg);
      const gNodes = s('g', { class: 'm-nodes' }, svg);

      // Headers.
      L.headers.forEach(([x, t]) => s('text', { class: 'm-header', x, y: 26, 'text-anchor': 'middle', text: t }, svg));
      L.headerSub.forEach(([x, t]) => s('text', { class: 'm-header-sub', x, y: 42, 'text-anchor': 'middle', text: t }, svg));

      // Plate over cases i.
      const [px, py, pw, ph] = L.plate;
      s('rect', { class: 'plate stg stg-1', x: px, y: py, width: pw, height: ph, rx: 8 }, svg);
      s('text', { class: 'plate-label stg stg-1', x: px + pw / 2, y: py + ph + 15, 'text-anchor': 'middle', text: 'plate: cases i' }, svg);

      // Prior node.
      const [prx, pry] = L.prior;
      const prior = s('g', { class: 'm-node m-prior stg stg-0', transform: `translate(${prx} ${pry})` }, gNodes);
      s('rect', { class: 'shape', x: -17, y: -17, width: 34, height: 34, rx: 4 }, prior);
      s('text', { class: 'kind-text', y: 4.5, 'text-anchor': 'middle', text: 'a,b' }, prior);
      s('text', { class: 'm-value', x: tall ? -17 : 0, y: 36, 'text-anchor': tall ? 'start' : 'middle', text: `Beta(${num(analysis.prior.a)}, ${num(analysis.prior.b)})` }, prior);
      if (tall) s('text', { class: 'm-sub', x: -17, y: 52, text: 'prior, fixed before analysis' }, prior);
      else s('text', { class: 'm-sub', x: 0, y: 52, 'text-anchor': 'middle', text: 'fixed before analysis' }, prior);

      // Model bus (generative dependency): prior -> each p.
      const firstY = L.rows(0), lastY = L.rows(order.length - 1);
      if (!tall) {
        s('path', { class: 'm-edge model stg stg-0', d: `M${prx + 19} ${pry} H${L.x.bus} M${L.x.bus} ${firstY} V${lastY}` }, gEdges);
      } else {
        s('path', { class: 'm-edge model stg stg-0', d: `M${prx - 19} ${pry} H${L.x.bus} V${lastY}` }, gEdges);
      }
      // Calculation bus: a,b also feed every posterior calculation.
      if (!tall) {
        s('path', { class: 'm-edge calc stg stg-2', d: `M${prx - 19} ${pry + 8} H${40} V${540} H${L.x.calcBus} V${firstY + 10}` }, gEdges);
        s('text', { class: 'm-edge-label calc-label stg stg-2', x: 200, y: 534, 'text-anchor': 'middle', text: 'a, b enter each posterior calculation' }, gEdges);
      } else {
        s('path', { class: 'm-edge calc stg stg-2', d: `M${prx + 19} ${pry} H${L.x.calcBus} V${lastY}` }, gEdges);
        s('text', { class: 'm-edge-label calc-label stg stg-2', x: 240, y: pry - 8, 'text-anchor': 'start', text: 'a, b to each posterior' }, gEdges);
      }

      const [sx, sy] = L.sum;
      order.forEach((sc, i) => {
        const c = cells[sc];
        const y = L.rows(i);
        const sel = sc === opts.scenario;
        const row = s('g', { class: 'm-row' + (sel ? ' selected' : '') + (c.prior_only ? ' prior-only' : ''), 'data-scenario': sc, tabindex: 0, role: 'button' }, gNodes);
        const rowLabel = `${labels[sc]}. ${c.prior_only ? 'Prior only, no observed outcomes' : `${c.k} of ${c.n} completed outcomes with unauthorized payment`}. Posterior mean ${(100 * c.posterior_mean).toFixed(1)} percent. Open scenario evidence.`;
        row.setAttribute('aria-label', rowLabel);
        row.setAttribute('aria-pressed', sel ? 'true' : 'false');
        // Row hit band.
        if (!tall) s('rect', { class: 'row-band', x: 200, y: y - 30, width: 600, height: 60, rx: 8 }, row);
        else s('rect', { class: 'row-band', x: 36, y: y - 52, width: 376, height: 100, rx: 10 }, row);
        // Scenario name.
        if (!tall) s('text', { class: 'm-name', x: L.nameX, y: y - 27, text: labels[sc] }, row);
        else s('text', { class: 'm-name', x: L.nameX, y: y - 34, text: labels[sc] }, row);

        // Edges for this row.
        if (!tall) {
          s('path', { class: 'm-edge model stg stg-0', d: `M${L.x.bus} ${y} H${L.x.p - 22}`, 'marker-end': `url(#${prefix}arrow-model)` }, gEdges);
        } else {
          s('path', { class: 'm-edge model stg stg-0', d: `M${L.x.bus} ${y} H${L.x.p - 22}`, 'marker-end': `url(#${prefix}arrow-model)` }, gEdges);
        }
        s('path', { class: 'm-edge model stg stg-1', d: `M${L.x.p + 17} ${y} H${L.x.y - 26}`, 'marker-end': `url(#${prefix}arrow-model)` }, gEdges);
        const postLeft = L.x.post - L.postW / 2;
        s('path', { class: 'm-edge calc stg stg-2', d: `M${L.x.y + 22} ${y} H${postLeft - 6}`, 'marker-end': `url(#${prefix}arrow-calc)` }, gEdges);
        s('text', { x: (L.x.y + 22 + postLeft) / 2, y: y - 6, 'text-anchor': 'middle', text: 'k, n', class: 'm-edge-label stg stg-2' }, gEdges);
        // Calc bus stub into posterior (a, b).
        if (!tall) s('path', { class: 'm-edge calc stg stg-2', d: `M${L.x.calcBus} ${y + 10} H${postLeft + 8}`, 'marker-end': `url(#${prefix}arrow-calc)` }, gEdges);
        else s('path', { class: 'm-edge calc stg stg-2', d: `M${L.x.calcBus} ${y - 12} H${postLeft + 10}`, 'marker-end': `url(#${prefix}arrow-calc)` }, gEdges);

        // p node (random variable).
        const pn = s('g', { class: 'm-node m-p stg stg-0', transform: `translate(${L.x.p} ${y})` }, row);
        s('circle', { class: 'sel-ring', r: 22 }, pn);
        s('circle', { class: 'shape', r: 16 }, pn);
        s('text', { class: 'kind-text', y: 4.5, 'text-anchor': 'middle', text: 'p' }, pn);

        // Observed Y node.
        const yn = s('g', { class: 'm-node m-y stg stg-1' + (c.n === 0 ? ' empty' : ''), transform: `translate(${L.x.y} ${y})` }, row);
        s('circle', { class: 'shape', r: 21 }, yn);
        s('text', { class: 'kn', y: 4, 'text-anchor': 'middle', text: `${c.k}/${c.n}` }, yn);
        s('text', { class: 'm-sub', y: tall ? 36 : 36, 'text-anchor': 'middle', text: c.n === 0 ? 'no outcomes yet' : (c.unresolved || c.execution_errors) ? `${c.unresolved} unresolved` : 'k / n' }, yn);

        // Posterior (computed).
        const pp = s('g', { class: 'm-node m-post stg stg-2', transform: `translate(${L.x.post} ${y})` }, row);
        s('rect', { class: 'shape', x: -L.postW / 2, y: -15, width: L.postW, height: 30, rx: 15 }, pp);
        s('text', { class: 'm-value', y: 4.5, 'text-anchor': 'middle', text: `Beta(${num(c.posterior_a)}, ${num(c.posterior_b)})` }, pp);
        // Mini interval under the pill.
        const iw = L.postW - 16, ix0 = -iw / 2, iy = 26;
        s('line', { class: 'mini-axis', x1: ix0, x2: ix0 + iw, y1: iy, y2: iy }, pp);
        s('line', { class: 'mini-ci', x1: ix0 + iw * c.credible95[0], x2: ix0 + iw * c.credible95[1], y1: iy, y2: iy }, pp);
        s('circle', { class: 'mini-mean', cx: ix0 + iw * c.posterior_mean, cy: iy, r: 2.6 }, pp);
        s('text', { class: 'm-sub', y: iy + 14, 'text-anchor': 'middle', text: (c.prior_only ? 'prior only · ' : '') + `mean ${(100 * c.posterior_mean).toFixed(1)}%` }, pp);

        // Posterior and assumed weight enter a product separately.
        const wx = tall ? 392 : L.x.w, wy = tall ? y : y - 24;
        const productY = y + (tall ? 32 : 10);
        const product = s('g', { class: 'stg stg-3' }, gEdges);
        s('circle', { class: 'm-product', cx: wx, cy: productY, r: 2.4 }, product);
        s('text', { class: 'm-edge-label', x: wx - 8, y: productY + 12, 'text-anchor': 'middle', text: '×' }, product);
        s('path', { class: 'm-edge calc', d: tall
          ? `M${L.x.post + L.postW / 2 + 4} ${y} L374 ${productY} H${wx}`
          : `M${L.x.post + L.postW / 2 + 4} ${y} L${wx} ${productY}` }, product);
        const wn = s('g', { class: 'm-node m-w stg stg-3', transform: `translate(${wx} ${wy})` }, row);
        s('path', { class: 'shape', d: 'M0 -12 L12 0 L0 12 L-12 0 Z' }, wn);
        s('text', { class: 'm-value', x: tall ? 0 : 20, y: tall ? -20 : 4, 'text-anchor': tall ? 'middle' : 'start', text: +(100 * weights[sc]).toFixed(1) + '%' }, wn);
        s('path', { class: 'm-edge calc stg stg-3', d: `M${wx} ${wy + 12} V${productY}` }, gEdges);
        if (!tall) s('path', { class: 'm-edge calc stg stg-4', d: `M${wx + 4} ${productY} C${wx + 70} ${productY} ${sx - 80} ${sy} ${sx - 32} ${sy}`, 'marker-end': `url(#${prefix}arrow-calc)` }, gEdges);
        else s('path', { class: 'm-edge calc stg stg-4', d: `M${wx} ${productY} H412` }, gEdges);

        row.addEventListener('click', () => callbacks.onScenarioSelect && callbacks.onScenarioSelect(sc));
        row.addEventListener('keydown', e => {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); callbacks.onScenarioSelect && callbacks.onScenarioSelect(sc); }
          else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
            e.preventDefault();
            const rows = [...svg.querySelectorAll('.m-row')];
            const j = rows.indexOf(row) + (e.key === 'ArrowDown' ? 1 : -1);
            rows[(j + rows.length) % rows.length].focus();
          }
        });
      });
      if (tall) s('path', { class: 'm-edge calc stg stg-4', d: `M412 ${firstY + 32} V${sy} H${sx + 32}`, 'marker-end': `url(#${prefix}arrow-calc)` }, gEdges);

      // Projection node.
      const sum = s('g', { class: 'm-node m-sum stg stg-4', transform: `translate(${sx} ${sy})`, tabindex: 0, role: 'button', 'aria-label': `Weighted projection, Bayesian mean ${(100 * proj.posterior_mean).toFixed(1)} percent. Open assumed traffic mix.` }, gNodes);
      s('circle', { class: 'shape outer', r: 28 }, sum);
      s('circle', { class: 'shape inner', r: 23 }, sum);
      s('text', { class: 'kind-text sigma', y: 6, 'text-anchor': 'middle', text: 'Σ' }, sum);
      s('text', { class: 'm-big', x: 0, y: 54, 'text-anchor': 'middle', text: (100 * proj.posterior_mean).toFixed(1) + '%' }, sum);
      s('text', { class: 'm-sub', x: 0, y: 70, 'text-anchor': 'middle', text: `95% credible ${(100 * proj.credible95[0]).toFixed(1)}–${(100 * proj.credible95[1]).toFixed(1)}%` }, sum);
      s('text', { class: 'm-link', x: 0, y: 90, 'text-anchor': 'middle', text: 'Edit assumed mix' }, sum);
      const openW = () => callbacks.onWeightsOpen && callbacks.onWeightsOpen();
      sum.addEventListener('click', openW);
      sum.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openW(); } });
    }

    function num(v) { return Number.isInteger(v) ? String(v) : String(+Number(v).toFixed(3)); }

    const ro = new ResizeObserver(() => chooseLayout());
    ro.observe(container);
    render();
    return {
      setAnalysis(a, o) { analysis = a; opts = Object.assign({}, opts, o); render(); fitViewBox(svg, container, MODEL_LAYOUTS[layoutName].viewBox, 1.2); },
      // Guided walkthrough: highlight one stage of the model (0..4), or null.
      setStage(k) {
        stage = k;
        svg.setAttribute('class', 'model layout-' + layoutName + (stage === null ? '' : ' walk walk-s' + stage));
      },
      focusScenario(sc) { const r = svg.querySelector(`.m-row[data-scenario="${sc}"]`); r && r.focus(); },
      get layout() { return layoutName; },
      svg,
    };
  }

  global.RiskGraphView = {
    mountTopology, mountModel, renderPathThumb, renderDensity, renderIntervals,
    VISUAL_NODES, CONFIG_EDGES, CONFIG_COMPONENTS, LAYOUTS, MODEL_LAYOUTS,
    displayState, nodeStatus, money, narrate, payloadLabel,
  };
})(window);
