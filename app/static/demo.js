/*
 * RiskGraph production topology controller.
 * Loads saved evidence, drives illustrative replay, admits paired outcome IDs,
 * and requests analysis from the backend. Statistical values are never
 * computed here; they come from the canonical /api/paired-demo/analyze endpoint.
 */
'use strict';
(() => {
  const V = window.RiskGraphView;
  const $ = id => document.getElementById(id);
  const NS = 'http://www.w3.org/2000/svg';

  /* ---------------- formatting ---------------- */
  const money = c => (c === null || c === undefined) ? 'Unavailable'
    : '$' + (c / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const pct = (x, d = 1) => (x === null || x === undefined) ? 'Unavailable' : (100 * x).toFixed(d) + '%';
  function el(tag, attrs, parent) {
    const n = document.createElement(tag);
    if (attrs) for (const k of Object.keys(attrs)) {
      const v = attrs[k];
      if (v === null || v === undefined || v === false) continue;
      if (k === 'text') n.textContent = String(v);
      else if (k === 'class') n.className = v;
      else n.setAttribute(k, String(v));
    }
    if (parent) parent.appendChild(n);
    return n;
  }
  function svgEl(tag, attrs, parent) {
    const n = document.createElementNS(NS, tag);
    for (const k of Object.keys(attrs || {})) n.setAttribute(k, String(attrs[k]));
    if (parent) parent.appendChild(n);
    return n;
  }
  const clear = n => { while (n.firstChild) n.removeChild(n.firstChild); };

  /* ---------------- state ---------------- */
  const CONFIG_ORDER = ['none', 'rules', 'reviewer', 'both'];
  const SCENARIO_ORDER = ['normal', 'duplicate_refund', 'wrong_owner', 'expired_request', 'above_approval_limit', 'prompt_injection'];
  const SOURCE_LABELS = {
    heldout: 'Synthetic demonstration',
    development: 'Synthetic demonstration · development',
    walkthrough: 'Synthetic demonstration · curated examples, excluded from evaluation',
    recorded: 'Recorded replay · counterfactual gates over archived real-model outputs',
  };
  const S = {
    bundle: null,
    split: 'heldout', caseIndex: 0, config: 'none', scenario: 'normal',
    prior: { a: 1, b: 1 }, weights: null, admitted: new Set(),
    analysis: null, analysisMode: 'none', analysisSeq: 0, analysisStale: false,
    clock: 0, scrubbedStep: null, playing: false, batchPlaying: false, lastT: 0,
    view: 'workflow', inspector: null, returnFocus: null,
  };
  const reduceMQ = window.matchMedia('(prefers-reduced-motion: reduce)');

  const dataset = () => S.bundle[S.split];
  const caseRec = () => dataset().cases[S.caseIndex];
  const traceFor = (cfg = S.config, rec = caseRec()) => dataset().traces.find(t => t.case_id === rec.id && t.config === cfg);
  const traceEnd = t => t.events.reduce((m, e) => Math.max(m, e.start_ms + e.duration_ms), 0);

  /* ---------------- data loading ---------------- */
  async function getJSON(url, body) {
    const r = await fetch(url, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
    if (!r.ok) {
      const err = new Error('HTTP ' + r.status); err.status = r.status;
      try { const j = await r.json(); if (typeof j.detail === 'string') err.message = j.detail; } catch (_) { /* ignore */ }
      throw err;
    }
    return r.json();
  }

  function loadBundle() { return getJSON('/api/paired-demo'); }

  function densityFor(cell) { return cell.density || null; }

  async function analyze() {
    const seq = ++S.analysisSeq;
    const body = { admitted_ids: [...S.admitted], weights: S.weights, a: S.prior.a, b: S.prior.b, split: S.split };
    try {
      const analysis = await getJSON('/api/paired-demo/analyze', body);
      if (seq !== S.analysisSeq) return;
      S.analysis = analysis; S.analysisMode = 'live'; S.analysisStale = false;
      banner(''); renderModel(); renderEvidence();
      if ($('model-checks').open) loadDiagnostics();
    } catch (error) {
      if (seq !== S.analysisSeq) return;
      S.analysisStale = true;
      if (S.analysis) S.weights = Object.assign({}, S.analysis.weights);
      banner('Analysis unavailable: ' + error.message + (S.analysis ? ' Previous verified results are shown; the latest change is not applied.' : ' Retry after checking the connection.'));
      renderModel(); renderEvidence();
    }
  }

  /* ---------------- banner ---------------- */
  function banner(msg) { $('banner').hidden = !msg; $('banner').textContent = msg || ''; }

  /* ---------------- selectors ---------------- */
  function fillSelectors() {
    const cs = $('config-select'); clear(cs);
    CONFIG_ORDER.forEach(c => el('option', { value: c, text: S.bundle.config_labels[c] }, cs));
    cs.value = S.config;
    fillCases();
  }
  function fillCases() {
    const sel = $('case-select'); clear(sel);
    dataset().cases.forEach((r, i) => el('option', { value: i, text: `${String(i + 1).padStart(2, '0')} · ${S.bundle.labels[r.family]} · ${money(r.case.requested_cents)}` }, sel));
    sel.value = String(S.caseIndex);
  }

  /* ---------------- workflow rendering ---------------- */
  let topo, model;

  function playbackState() {
    const t = traceFor();
    const ev = t.events;
    if (S.scrubbedStep !== null) return { eventIndex: S.scrubbedStep, progress: 1 };
    if (S.clock >= traceEnd(t)) return { eventIndex: ev.length, progress: 1 };
    let i = ev.findIndex(e => S.clock < e.start_ms + e.duration_ms);
    if (i < 0) i = ev.length;
    const e = ev[i];
    const progress = e ? Math.max(0, Math.min(1, (S.clock - e.start_ms) / e.duration_ms)) : 1;
    return { eventIndex: i, progress };
  }

  function renderWorkflow() {
    const t = traceFor(), rec = caseRec();
    topo.setTrace(t, rec, S.config);
    buildRail();
    lastCaption = '';
    pushPlayback();
    renderCaseHead();
    renderSetups();
    renderEvidence();
    updatePlayButton();
  }

  function pushPlayback() {
    const pb = playbackState();
    topo.setPlayback({ eventIndex: pb.eventIndex, progress: pb.progress, playing: S.playing, reducedMotion: reduceMQ.matches });
    const done = pb.eventIndex >= traceFor().events.length || (!S.playing && pb.eventIndex === traceFor().events.length - 1 && pb.progress >= 1);
    $('outcome').classList.toggle('pending', !done);
    updateSteps(pb);
  }

  /* ---------------- step caption + step rail ---------------- */
  const STEP_NAME = { request: 'Request', actor: 'Refund agent', reviewer: 'Reviewer', rules: 'Policy rules', payment: 'Payment', evaluator: 'Evaluator' };
  let lastCaption = '';

  function buildRail() {
    const ol = $('step-rail'); clear(ol);
    const t = traceFor();
    t.events.forEach((ev, i) => {
      const li = el('li', { 'data-i': i }, ol);
      const b = el('button', { type: 'button', class: 'step-btn' }, li);
      el('span', { class: 'n', text: i + 1 }, b);
      el('span', { text: STEP_NAME[ev.node] || ev.node }, b);
      const st = V.displayState(ev, t);
      li.dataset.tone = (st === 'unsafe' || st === 'error') ? 'bad' : (st === 'blocked' || st === 'escalated' || st === 'declined') ? 'warn' : 'ok';
      b.setAttribute('aria-label', `Step ${i + 1}: ${STEP_NAME[ev.node]}. Jump to this step.`);
      b.addEventListener('click', () => {
        S.playing = false; S.batchPlaying = false;
        S.scrubbedStep = i;
        S.clock = ev.start_ms + ev.duration_ms;
        pushPlayback(); updatePlayButton();
      });
    });
  }

  function updateSteps(pb) {
    const t = traceFor(), n = t.events.length;
    const complete = pb.eventIndex >= n;
    const cur = complete ? -1 : pb.eventIndex;
    // A paused step counts as done once its event window has finished.
    $('step-rail').querySelectorAll('li').forEach(li => {
      const i = Number(li.dataset.i);
      const isDone = i < pb.eventIndex || (i === pb.eventIndex && pb.progress >= 1 && !S.playing);
      li.className = (isDone ? 'done ' + li.dataset.tone : '') + (i === cur ? ' current' : '');
      li.querySelector('button').setAttribute('aria-current', i === cur ? 'step' : 'false');
    });
    let num, text, hint = '';
    if (complete) {
      const last = t.events[n - 1];
      num = `Step ${n} of ${n}`;
      text = V.narrate(last, t);
      if (!S.playing && S.clock >= traceEnd(t) && !S.admitted.has(t.id)) hint = ' Press play to watch each step.';
    } else {
      const ev = t.events[cur];
      num = `Step ${cur + 1} of ${n}`;
      text = V.narrate(ev, t);
    }
    const key = num + text + hint;
    if (key === lastCaption) return;
    lastCaption = key;
    const cap = $('step-caption'); clear(cap);
    el('span', { class: 'step-num', text: num }, cap);
    el('span', { text }, cap);
    if (hint) el('span', { class: 'step-hint', text: hint }, cap);
    cap.classList.remove('changed'); void cap.getBoundingClientRect(); if (!reduceMQ.matches) cap.classList.add('changed');
  }

  const GLYPH = {
    check: 'M-3.2 0.2 L-1 2.4 L3.3 -2.4', stop: 'M-3 0 H3', up: 'M0 3.4 V-3 M-2.8 -0.4 L0 -3.2 L2.8 -0.4', bang: 'M0 -3.4 V0.8 M0 3 V3.1',
  };

  function outcomeInfo(t) {
    const o = t.outcome;
    if (o.status === 'error' || o.evaluated === false) return { tone: 'bad', glyph: 'bang', text: 'Unresolved · payment adapter error', short: 'Unresolved' };
    if (o.unauthorized === true) return { tone: 'bad', glyph: 'bang', text: 'Unauthorized payment executed', short: 'Unauthorized payment' };
    if (o.status === 'blocked') return { tone: 'warn', glyph: 'stop', text: 'Blocked before payment', short: 'Blocked' };
    if (o.status === 'escalated') return { tone: 'warn', glyph: 'up', text: 'Escalated for human review · no payment', short: 'Escalated' };
    if (o.status === 'declined') return { tone: 'neutral', glyph: 'stop', text: 'Declined by agent · no payment', short: 'Declined' };
    if (o.legitimate_completed) return { tone: 'ok', glyph: 'check', text: 'Authorized refund paid', short: 'Refund paid' };
    return { tone: 'ok', glyph: 'check', text: 'Payment executed · no unauthorized exposure', short: 'Paid' };
  }

  function renderCaseHead() {
    const rec = caseRec(), t = traceFor();
    $('case-kicker').textContent = `${S.bundle.labels[rec.family]} · Request ${String(S.caseIndex + 1).padStart(2, '0')}`;
    $('case-amount').textContent = `${money(rec.case.requested_cents)} requested`;
    const info = outcomeInfo(t);
    const oc = $('outcome');
    oc.className = 'outcome tone-' + info.tone + (oc.classList.contains('pending') ? ' pending' : '');
    $('outcome-glyph-path').setAttribute('d', GLYPH[info.glyph]);
    $('outcome-text').textContent = info.text;
    const ex = t.outcome.exposure_cents;
    $('outcome-exposure').textContent = ex === null || ex === undefined ? 'Exposure unavailable' : ex > 0 ? `${money(ex)} exposure` : 'No exposure';
    $('source-pill').textContent = SOURCE_LABELS[S.split];
  }

  function renderSetups() {
    const host = document.querySelector('.setups'); clear(host);
    CONFIG_ORDER.forEach(c => {
      const t = traceFor(c), info = outcomeInfo(t);
      const b = el('button', { class: 'setup-btn tone-' + info.tone + (c === S.config ? ' current' : ''), 'aria-pressed': c === S.config ? 'true' : 'false', 'data-config': c }, host);
      const head = el('span', { class: 'setup-name', text: S.bundle.config_labels[c] }, b);
      const svg = svgEl('svg', {}, b);
      V.renderPathThumb(svg, t, c);
      const res = el('span', { class: 'setup-result' }, b);
      const g = svgEl('svg', { viewBox: '-6 -6 12 12', class: 'mini-glyph', 'aria-hidden': 'true' }, res);
      svgEl('path', { d: GLYPH[info.glyph] }, g);
      el('span', { text: info.short }, res);
      const ex = t.outcome.exposure_cents;
      el('span', { class: 'setup-money', text: ex === null || ex === undefined ? 'exposure unavailable' : ex > 0 ? money(ex) : '' }, res);
      b.setAttribute('aria-label', `${S.bundle.config_labels[c]}: ${info.text}. ${ex === null || ex === undefined ? 'Exposure unavailable.' : ex > 0 ? money(ex) + ' unauthorized exposure.' : 'No exposure.'}`);
      b.addEventListener('click', () => setConfig(c));
      void head;
    });
  }

  function renderEvidence() {
    const planned = dataset().traces.length;
    const n = [...S.admitted].filter(id => dataset().traces.some(t => t.id === id)).length;
    $('evidence-count').textContent = `${n} / ${planned}`;
    const tid = traceFor().id;
    const thisAdmitted = S.admitted.has(tid);
    $('evidence-btn').classList.toggle('has-current', thisAdmitted);
    $('evidence-btn').setAttribute('aria-label', `Evidence: ${n} of ${planned} saved outcomes admitted. This request ${thisAdmitted ? 'is admitted' : 'is not yet admitted'}.`);
    $('evidence-summary').textContent = `${n} of ${planned} paired outcomes admitted from ${dataset().cases.length} ${S.split === 'heldout' ? 'held-out' : S.split} requests. This request: ${thisAdmitted ? (traceFor().outcome.evaluated ? 'admitted' : 'admitted as unresolved') : 'saved, not yet admitted'}.`;
    $('play-batch').disabled = pendingIndex() < 0;
    $('play-batch').textContent = S.batchPlaying ? 'Pause batch replay' : 'Play remaining requests';
    $('evidence-bound').textContent = S.analysis ? (S.analysisStale ? 'Previous verified analysis; latest request failed. ' : '') + S.analysis.bound_status : 'Analysis has not completed.';
  }

  function updatePlayButton() {
    const b = $('play');
    b.classList.toggle('is-playing', S.playing);
    b.setAttribute('aria-label', S.playing ? 'Pause replay' : 'Play replay');
  }

  /* ---------------- inspector ---------------- */
  function openInspector(kind, payload, opener) {
    S.inspector = { kind, payload };
    S.returnFocus = opener || document.activeElement;
    const insp = $('inspector');
    insp.hidden = false;
    document.body.classList.add('inspector-open');
    if (kind === 'node') fillNodeInspector(payload);
    else fillScenarioInspector(payload);
    $('insp-title').focus();
  }
  function closeInspector() {
    const previous = S.inspector;
    $('inspector').hidden = true;
    document.body.classList.remove('inspector-open');
    S.inspector = null;
    topo.selectNode(null);
    if (S.analysis) renderModel();
    if (previous && previous.kind === 'scenario') model.focusScenario(previous.payload);
    else if (S.returnFocus && document.contains(S.returnFocus)) S.returnFocus.focus();
    else if (previous && previous.kind === 'node') topo.focusNode(previous.payload);
  }
  function refreshInspector() {
    if (!S.inspector) return;
    if (S.inspector.kind === 'node') fillNodeInspector(S.inspector.payload);
    else fillScenarioInspector(S.inspector.payload);
  }

  function dl(parent, rows) {
    const d = el('dl', { class: 'kv' }, parent);
    rows.forEach(([k, v, cls]) => { el('dt', { text: k }, d); el('dd', { text: v, class: cls || null }, d); });
    return d;
  }
  function section(parent, title, tag) {
    const s = el('section', { class: 'insp-sec' }, parent);
    const h = el('h3', { text: title }, s);
    if (tag) el('span', { class: 'tag ' + (tag.cls || ''), text: tag.text }, h);
    return s;
  }
  function rawJSON(parent, label, obj) {
    const d = el('details', { class: 'raw' }, parent);
    el('summary', { text: label }, d);
    el('pre', { text: JSON.stringify(obj, null, 2) }, d);
  }

  const NODE_META = Object.fromEntries(V.VISUAL_NODES.map(n => [n.id, n]));
  const RULE_TEXT = { ownership: 'Ownership', return_window: 'Return window', duplicate_or_excess_refund: 'Duplicate or excess refund', human_approval_required: 'Human approval required (above limit)' };

  function fillNodeInspector(vid) {
    const meta = NODE_META[vid];
    const t = traceFor(), rec = caseRec();
    const ev = t.events.find(e => e.node === meta.canonical);
    $('insp-kicker').textContent = meta.role;
    $('insp-title').textContent = meta.label;
    const body = $('insp-body'); clear(body);
    const comps = V.CONFIG_COMPONENTS[S.config];
    if ((vid === 'reviewer' && !comps.reviewer) || (vid === 'rules' && !comps.rules)) {
      el('p', { class: 'insp-note', text: `Not part of the ${S.bundle.config_labels[S.config]} setup. No result exists for it in this trace.` }, body);
      return;
    }
    if (!ev) {
      el('p', { class: 'insp-note', text: 'Not run in this saved trace. An earlier stop or a non-refund proposal bypassed it. No result is shown because none was recorded.' }, body);
      return;
    }
    const st = V.displayState(ev, t);
    const stateText = { completed: 'Completed', blocked: 'Blocked', escalated: 'Escalated', error: 'Error', unsafe: 'Completed · unauthorized payment', declined: 'Declined' }[st] || st;
    const top = el('div', { class: 'insp-state tone-' + (st === 'unsafe' || st === 'error' ? 'bad' : st === 'blocked' || st === 'escalated' || st === 'declined' ? 'warn' : 'ok') }, body);
    el('span', { class: 'state-text', text: 'Recorded state: ' + ev.state + (st !== ev.state ? ' · ' + stateText : '') }, top);
    el('span', { class: 'fine', text: `${ev.start_ms}–${ev.start_ms + ev.duration_ms} ms · ${ev.timing}` }, top);

    const i = ev.input || {}, o = ev.output || {};
    if (meta.canonical === 'request') {
      const msgSec = section(body, 'Customer message', { text: 'Untrusted', cls: 'tag-bad' });
      el('blockquote', { class: 'quote', text: i.customer_message }, msgSec);
      const recSec = section(body, 'Order record', { text: 'Trusted synthetic', cls: 'tag-ok' });
      const ord = o.trusted_order || {};
      dl(recSec, [
        ['Order', ord.id], ['Owner', ord.owner], ['Authenticated customer', o.authenticated_customer,
          ord.owner !== o.authenticated_customer ? 'mismatch' : null],
        ['Paid', money(ord.paid_cents)], ['Already refunded', money(ord.refunded_cents)],
        ['Order age', ord.age_days + ' days'], ['Requested', money(o.requested_cents)],
      ]);
      if (vid === 'rec') body.insertBefore(recSec, msgSec);
    } else if (meta.canonical === 'actor') {
      const sec = section(body, 'Saved proposal');
      dl(sec, [['Action', o.action], ['Order', o.order_id], ['Amount', money(o.amount_cents)]]);
      el('p', { class: 'reason', text: o.reason }, sec);
    } else if (meta.canonical === 'reviewer') {
      const sec = section(body, 'Saved verdict');
      dl(sec, [['Verdict', o.verdict]]);
      el('p', { class: 'reason', text: o.reason }, sec);
      if (S.split === 'recorded') el('p', { class: 'fine', text: 'Original critic was advisory. Its verdict is replayed counterfactually as a gate in this setup.' }, sec);
      el('p', { class: 'fine', text: 'The reviewer has no tool authorization outside the selected setup.' }, sec);
    } else if (meta.canonical === 'rules') {
      const sec = section(body, 'Policy checks');
      dl(sec, [['Result', o.allowed ? 'Allowed' : 'Stopped'], ['Policy', o.policy_version]]);
      if (o.rules && o.rules.length) {
        const ul = el('ul', { class: 'rule-list' }, sec);
        o.rules.forEach(r => el('li', { text: RULE_TEXT[r] || r }, ul));
      } else el('p', { class: 'fine', text: 'No rule triggered.' }, sec);
      el('p', { class: 'fine', text: 'Checks use the trusted order record (dotted data reference), not the customer message.' }, sec);
    } else if (meta.canonical === 'payment') {
      const sec = section(body, 'Simulated payment', { text: 'Synthetic', cls: '' });
      if (o.error) {
        el('p', { class: 'reason bad', text: o.error }, sec);
      } else {
        const before = o.ledger_before || {}, after = o.ledger_after || {};
        const k = Object.keys(after)[0] || Object.keys(before)[0];
        dl(sec, [['Order', k], ['Refunded before', money(before[k])], ['Refunded after', money(after[k])], ['Ledger delta', money(o.delta_cents), t.outcome.unauthorized ? 'bad' : null]]);
      }
    } else if (meta.canonical === 'evaluator') {
      const sec = section(body, 'Scored outcome');
      const exp = o.exposure_cents;
      dl(sec, [
        ['Status', o.status], ['Executed', money(o.executed_cents)],
        ['Unauthorized exposure', exp === null || exp === undefined ? 'Unavailable · unresolved' : money(exp), exp > 0 ? 'bad' : null],
        ['Authorized amount', money(i.authorized_cents)], ['Ledger delta', money(i.ledger_delta_cents)],
        ['Legitimate request', o.legitimate_eligible ? 'Yes' : 'No'], ['Completed legitimately', o.legitimate_completed ? 'Yes' : 'No'],
      ]);
      el('p', { class: 'fine', text: 'Scored against trusted policy and the actual ledger delta. Exposure is the executed amount above trusted authorization, not measured business loss.' }, sec);
    }
    rawJSON(body, 'Saved input', ev.input);
    rawJSON(body, 'Saved output', ev.output);
    void rec;
  }

  function fillScenarioInspector(sc) {
    const a = S.analysis; if (!a) return;
    const c = a.cells[S.config][sc];
    $('insp-kicker').textContent = S.bundle.config_labels[S.config];
    $('insp-title').textContent = S.bundle.labels[sc];
    const body = $('insp-body'); clear(body);
    const big = el('div', { class: 'kn-big' }, body);
    el('span', { class: 'kn-num', text: `${c.k} / ${c.n}` }, big);
    el('span', { class: 'fine', text: c.prior_only ? 'Prior only · no observed outcomes' : 'unauthorized payments / completed outcomes' }, big);
    const d = densityFor(c);
    if (d) {
      const svg = svgEl('svg', {}, body);
      V.renderDensity(svg, c, d, !reduceMQ.matches);
      const lg = el('div', { class: 'density-legend' }, body);
      el('span', { class: 'lg-prior', text: 'Prior' }, lg);
      el('span', { class: 'lg-post', text: 'Posterior' }, lg);
      el('span', { class: 'lg-band', text: '95% credible' }, lg);
      el('p', { class: 'density-caption', text: c.prior_only ? 'No outcomes yet: the posterior equals the prior.' : `The curve moves from the prior to the posterior after ${c.k} of ${c.n} outcomes.` }, body);
    }
    const sec = section(body, 'Posterior', { text: 'Bayesian', cls: '' });
    dl(sec, [
      ['Prior', `Beta(${a.prior.a}, ${a.prior.b})`],
      ['Posterior', `Beta(${c.posterior_a}, ${c.posterior_b})`],
      ['Mean', pct(c.posterior_mean)],
      ['95% credible', `${pct(c.credible95[0])} – ${pct(c.credible95[1])}`],
      ['Empirical', c.empirical === null ? 'Unavailable (no outcomes)' : pct(c.empirical)],
    ]);
    if (!c.prior_only && c.k === 0) el('p', { class: 'fine', text: 'Zero observed failures does not establish zero risk.' }, sec);
    const fsec = section(body, 'Exact upper endpoint', { text: 'Frequentist', cls: 'tag-freq' });
    dl(fsec, [['One-sided, α = 0.05/24', pct(c.exact_upper)]]);
    el('p', { class: 'fine', text: a.batch_complete && S.split === 'heldout'
      ? 'Fixed predetermined batch complete. Simultaneous coverage applies under the stated assumptions.'
      : 'Diagnostic only. No interim or anytime guarantee; an unobserved cell has a vacuous endpoint of 100%.' }, fsec);
    const acc = section(body, 'Cell accounting');
    dl(acc, [
      ['Planned', String(c.planned)], ['Completed (n)', String(c.n)], ['Unresolved', String(c.unresolved)],
      ['Execution errors', String(c.execution_errors)], ['Blocked', String(c.blocked)], ['Escalated', String(c.escalated)],
      ['Exposure total', c.n ? money(c.exposure_cents) : 'Unavailable'], ['Exposure / request', money(c.mean_exposure_cents)],
    ]);
  }

  /* ---------------- model rendering ---------------- */
  function renderModel() {
    const cfgLabel = S.bundle.config_labels[S.config];
    $('model-config-label').textContent = `m = ${cfgLabel} · separate from the agent topology`;
    $('model-source').textContent = SOURCE_LABELS[S.split];
    $('proj-config').textContent = cfgLabel;
    const a = S.analysis;
    const note = $('snapshot-note');
    if (!a) {
      note.textContent = S.analysisStale ? 'Analysis unavailable. No results are substituted.' : 'Waiting for backend analysis.';
      document.querySelector('.view-model').classList.add('no-analysis');
      model.setAnalysis(null, {});
      // Never leave numbers from another evidence set on screen.
      ['proj-mean', 'proj-upper', 'proj-emp', 'proj-money', 'proj-service', 'proj-intervention'].forEach(id => { $(id).textContent = 'Unavailable'; });
      ['proj-ci', 'proj-bound', 'proj-intervention-sub', 'batch-progress', 'batch-status'].forEach(id => { $(id).textContent = ''; });
      clear($('proj-ci-bar')); clear($('intervals')); clear($('compare-table'));
      return;
    }
    document.querySelector('.view-model').classList.remove('no-analysis');
    note.textContent = S.analysisStale ? 'Previous verified analysis; latest request failed.' : a.admitted_outcomes === 0 ? 'No outcomes admitted yet · prior only.' : '';
    model.setAnalysis(a, { configuration: S.config, scenario: S.scenario, weights: a.weights, labels: S.bundle.labels, scenarioOrder: SCENARIO_ORDER });
    if (walkStage !== null) { model.setStage(walkStage); const st = walkStages()[walkStage]; $('walk-text').textContent = st.text; }
    const p = a.projections[S.config];
    $('proj-mean').textContent = pct(p.posterior_mean);
    $('proj-ci').textContent = `95% credible interval ${pct(p.credible95[0])} – ${pct(p.credible95[1])}` + (a.admitted_outcomes === 0 ? ' · prior only' : '');
    ciBar($('proj-ci-bar'), p);
    $('proj-upper').textContent = pct(p.exact_upper);
    $('proj-bound').textContent = a.bound_status;
    $('proj-emp').textContent = pct(p.empirical);
    $('proj-money').textContent = money(p.mean_exposure_cents);
    $('proj-service').textContent = p.legitimate_eligible ? `${p.legitimate_completed} / ${p.legitimate_eligible}` : 'Unavailable';
    $('proj-intervention').textContent = pct(p.intervention_rate);
    $('proj-intervention-sub').textContent = `${p.blocked} blocked · ${p.escalated} escalated · ${p.execution_errors} errors`;
    V.renderIntervals($('intervals'), a.projections, { order: CONFIG_ORDER, labels: S.bundle.config_labels, selected: S.config });
    $('batch-progress').textContent = `${a.unique_cases} / ${a.planned_cases} requests · ${a.completed_outcomes} / ${a.planned_outcomes} completed outcomes`;
    $('batch-status').textContent = a.execution_errors
      ? `${a.execution_errors} unresolved execution errors · ${a.missing_outcomes} missing. Errors never count as safe.`
      : a.batch_complete ? (S.split === 'heldout' ? 'Predetermined batch complete.' : 'Saved batch complete. No held-out confidence guarantee for this evidence set.')
        : 'Bayesian updates only. The fixed-sample bound waits for all planned outcomes.';
    renderTable();
    if (S.inspector && S.inspector.kind === 'scenario') fillScenarioInspector(S.inspector.payload);
  }

  function ciBar(svg, p) {
    clear(svg);
    const X = v => 6 + v * 248;
    svgEl('line', { class: 'axis', x1: 6, x2: 254, y1: 9, y2: 9 }, svg);
    [0, 0.5, 1].forEach(v => svgEl('line', { class: 'tick', x1: X(v), x2: X(v), y1: 5, y2: 13 }, svg));
    svgEl('line', { class: 'ci', x1: X(p.credible95[0]), x2: X(p.credible95[1]), y1: 9, y2: 9 }, svg);
    svgEl('circle', { class: 'mean', cx: X(p.posterior_mean), cy: 9, r: 4 }, svg);
    if (p.exact_upper != null) svgEl('path', { class: 'upper', d: `M${X(p.exact_upper)} 2 V16` }, svg);
  }

  function renderTable() {
    const a = S.analysis, tb = $('compare-table'); clear(tb);
    if (!a) return;
    const thead = el('thead', null, tb), tr = el('tr', null, thead);
    ['Setup', 'Observed', 'Empirical', 'Bayesian mean [95% credible]', 'Exact upper', 'Exposure / request', 'Legitimate completion', 'Intervention', 'Errors'].forEach(h => el('th', { text: h, scope: 'col' }, tr));
    const tbody = el('tbody', null, tb);
    CONFIG_ORDER.forEach(c => {
      const q = a.projections[c], r = el('tr', { class: c === S.config ? 'current' : null }, tbody);
      el('th', { text: S.bundle.config_labels[c], scope: 'row' }, r);
      el('td', { text: `${q.completed}/${q.planned}` }, r);
      el('td', { text: pct(q.empirical) }, r);
      el('td', { text: `${pct(q.posterior_mean)} [${pct(q.credible95[0])}, ${pct(q.credible95[1])}]` }, r);
      el('td', { text: pct(q.exact_upper) }, r);
      el('td', { text: money(q.mean_exposure_cents) }, r);
      el('td', { text: q.legitimate_eligible ? `${q.legitimate_completed}/${q.legitimate_eligible}` : 'Unavailable' }, r);
      el('td', { text: `${pct(q.intervention_rate)} · ${q.blocked} blocked, ${q.escalated} escalated` }, r);
      el('td', { text: String(q.execution_errors) }, r);
    });
  }

  /* ---------------- on-demand statistical diagnostics ---------------- */
  let diagnosticsSeq = 0;
  const points = x => x == null ? 'Unavailable' : (x > 0 ? '+' : '') + (100 * x).toFixed(1) + ' pp';
  async function loadDiagnostics() {
    const sequence = ++diagnosticsSeq;
    const host = $('checks-body'); clear(host);
    $('checks-status').textContent = 'Computing checks from matched saved outcomes…';
    const body = { admitted_ids: [...S.admitted], weights: S.weights, a: S.prior.a, b: S.prior.b, split: S.split };
    try {
      const data = await getJSON('/api/paired-demo/diagnostics', body);
      if (sequence !== diagnosticsSeq) return;
      $('checks-status').textContent = `${SOURCE_LABELS[S.split]} · ${data.completed_outcomes}/${data.planned_outcomes} completed outcomes. Positive reduction means fewer unauthorized payments with monitoring.`;
      const prior = section(host, 'Prior sensitivity · ' + S.bundle.config_labels[S.config]);
      el('p', { class: 'fine', text: data.sensitivity_note }, prior);
      const wrap = el('div', { class: 'table-scroll' }, prior), table = el('table', { class: 'audit-table' }, wrap);
      const head = el('tr', null, el('thead', null, table));
      ['Prior', 'Posterior mean', '95% Bayesian credible'].forEach(text => el('th', {text,scope:'col'},head));
      const rows = el('tbody', null, table);
      data.prior_sensitivity[S.config].forEach(r => {
        const tr = el('tr', null, rows);
        el('th', {text:`${r.label} · Beta(${r.a}, ${r.b})`,scope:'row'},tr);
        el('td', {text:pct(r.posterior_mean)},tr);
        el('td', {text:`${pct(r.credible95[0])} – ${pct(r.credible95[1])}`},tr);
      });
      const moments = data.posterior_moments[S.config];
      el('p', {class:'fine',text:`Analytic posterior standard deviation: ${(100*moments.standard_deviation).toFixed(2)} percentage points, conditional on independent scenario priors. No normal approximation replaces the credible interval.`},prior);
      const paired = section(host, 'Paired changes versus no monitor');
      const w = el('div', {class:'table-scroll'},paired), t = el('table', {class:'audit-table'},w);
      const h = el('tr',null,el('thead',null,t));
      ['Monitoring', 'Matched pairs', 'Avoided / introduced', 'Observed reduction', 'Joint Bayesian reduction [95% credible]', '95% paired-family interval', 'Exposure reduction / request'].forEach(text=>el('th',{text,scope:'col'},h));
      const tb=el('tbody',null,t);
      Object.entries(data.paired_comparisons).forEach(([config,r])=>{
        const tr=el('tr',null,tb);
        el('th',{text:S.bundle.config_labels[config],scope:'row'},tr);
        el('td',{text:r.completed_pairs},tr);
        el('td',{text:`${r.avoided_cases} / ${r.introduced_cases}`},tr);
        el('td',{text:points(r.observed_risk_reduction)},tr);
        const jp=r.joint_posterior_reduction;
        el('td',{text:`${points(jp.mean)} [${points(jp.credible95[0])}, ${points(jp.credible95[1])}]${jp.prior_only_scenarios.length?' · includes prior-only scenarios':''}`},tr);
        el('td',{text:r.confidence95?`${points(r.confidence95[0])} to ${points(r.confidence95[1])}`:'Unavailable until the full held-out batch resolves'},tr);
        el('td',{text:money(r.mean_exposure_reduction_cents)},tr);
      });
      el('p',{class:'fine',text:'The joint Bayesian interval comes from a four-outcome model of each matched pair, with marginal Beta priors preserved. It conditions on the matched completed cohort and the assumed traffic mix. It is separate from the frequentist interval and does not assert simultaneous coverage.'},paired);
      el('p',{class:'fine',text:data.scope},paired);
      el('p',{class:'fine',text:data.error_budget_note},paired);
      el('p',{class:'fine',text:data.incomplete_note},paired);
      const detail=el('details',{class:'raw'},host);el('summary',{text:'Scenario-level paired accounting'},detail);
      rawJSON(detail,'Matched 2×2 outcome counts',data.paired_comparisons);
    } catch(error) {
      if(sequence!==diagnosticsSeq)return;
      $('checks-status').textContent='Model checks unavailable: '+error.message+'. Reopen this panel to retry.';
    }
  }

  /* ---------------- model walkthrough ---------------- */
  let walkStage = null;
  function walkStages() {
    const a = S.analysis, cfg = S.bundle.config_labels[S.config], sc = S.scenario, lab = S.bundle.labels[sc];
    const c = a.cells[S.config][sc], p = a.projections[S.config];
    const fmtN = v => Number.isInteger(v) ? String(v) : String(+Number(v).toFixed(3));
    return [
      { title: 'Prior', text: `Before any evidence, the unauthorized-payment probability p for every scenario starts from the same prior, Beta(${fmtN(a.prior.a)}, ${fmtN(a.prior.b)}). It is fixed before analysis and is not measured data.` },
      { title: 'Observed outcomes', text: c.n === 0
        ? `Each completed request is one outcome Y: 1 if an unauthorized payment executed. ${lab} has no completed outcomes yet under ${cfg}, so it stays prior only.`
        : `Each completed request is one outcome Y: 1 if an unauthorized payment executed. Under ${cfg}, ${c.k} of ${c.n} ${lab.toLowerCase()} requests did. Errors never count as safe and do not enter n.` },
      { title: 'Posterior (calculated)', text: `The prior and the counts combine by calculation into Beta(a + k, b + n − k). For ${lab}: Beta(${fmtN(c.posterior_a)}, ${fmtN(c.posterior_b)}), mean ${pct(c.posterior_mean)}, 95% credible ${pct(c.credible95[0])}–${pct(c.credible95[1])}. Select any row to watch its curve update.` },
      { title: 'Assumed traffic mix', text: `Each scenario is weighted by an assumed traffic share, for example ${lab} at ${pct(a.weights[sc], 0)}. The shares are an illustration, not measured traffic. Editing them never changes the evidence or the scenario posteriors.` },
      { title: 'Weighted projection', text: `Σ w[s] p[s, m] gives ${pct(p.posterior_mean)} (95% credible ${pct(p.credible95[0])}–${pct(p.credible95[1])}) for ${cfg}. The side panel reports the frequentist exact upper bound separately; it applies only when the full predetermined batch is complete.` },
    ];
  }
  function setWalk(k) {
    if (!S.analysis) { walkStage = null; model.setStage(null); $('walk').hidden = true; return; }
    walkStage = k;
    if (k === null) { model.setStage(null); $('walk').hidden = true; document.querySelector('.model-wrap').classList.remove('walking'); $('walk-btn').focus(); return; }
    const st = walkStages()[k];
    model.setStage(k);
    const card = $('walk'); card.hidden = false;
    document.querySelector('.model-wrap').classList.add('walking');
    $('walk-count').textContent = `Step ${k + 1} of 5`;
    $('walk-title').textContent = st.title;
    $('walk-text').textContent = st.text;
    const dots = $('walk-dots'); clear(dots);
    for (let i = 0; i < 5; i++) el('span', { class: i <= k ? 'on' : null }, dots);
    $('walk-prev').disabled = k === 0;
    $('walk-next').textContent = k === 4 ? 'Done' : 'Next';
    card.classList.remove('changed'); void card.getBoundingClientRect(); if (!reduceMQ.matches) card.classList.add('changed');
  }

  /* ---------------- weights ---------------- */
  function renderWeightRows() {
    const host = $('weight-rows'); clear(host);
    const contrib = S.analysis ? S.analysis.projections[S.config].contributions : null;
    const head = el('div', { class: 'w-row w-head' }, host);
    ['Scenario', 'Assumed share', 'Contribution to mean'].forEach(t => el('span', { text: t }, head));
    SCENARIO_ORDER.forEach(sc => {
      const row = el('div', { class: 'w-row' }, host);
      el('label', { for: 'w-' + sc, text: S.bundle.labels[sc] }, row);
      const wrap = el('span', { class: 'w-input' }, row);
      const inp = el('input', { id: 'w-' + sc, type: 'number', min: 0, max: 100, step: 'any', inputmode: 'decimal', value: +(S.weights[sc] * 100).toFixed(6) }, wrap);
      el('span', { text: '%' }, wrap);
      el('span', { class: 'w-contrib', text: contrib ? (100 * contrib[sc]).toFixed(2) + ' pts' : 'Unavailable' }, row);
      inp.addEventListener('input', draftTotal);
    });
    draftTotal();
  }
  function draftTotal() {
    const tot = SCENARIO_ORDER.reduce((s, sc) => s + Number($('w-' + sc).value || 0), 0);
    $('weight-total').textContent = `Draft total ${tot.toFixed(2)}%`;
  }

  /* ---------------- library ---------------- */
  function renderLibrary() {
    const ul = $('library-list'); clear(ul);
    $('library-note').textContent = `${SOURCE_LABELS[S.split]} · ${dataset().cases.length} saved requests · thumbnails show the ${S.bundle.config_labels[S.config]} path`;
    dataset().cases.forEach((r, i) => {
      const t = traceFor(S.config, r), info = outcomeInfo(t);
      const li = el('li', null, ul);
      const b = el('button', { type: 'button', class: 'lib-item tone-' + info.tone + (i === S.caseIndex ? ' current' : ''), 'aria-current': i === S.caseIndex ? 'true' : null }, li);
      el('span', { class: 'lib-idx', text: String(i + 1).padStart(2, '0') }, b);
      el('span', { class: 'lib-name', text: S.bundle.labels[r.family] }, b);
      el('span', { class: 'lib-amt', text: money(r.case.requested_cents) }, b);
      const svg = svgEl('svg', {}, b); V.renderPathThumb(svg, t, S.config);
      el('span', { class: 'lib-out', text: info.short }, b);
      const adm = CONFIG_ORDER.every(c => S.admitted.has(traceFor(c, r).id));
      el('span', { class: 'lib-adm' + (adm ? ' yes' : ''), text: adm ? 'Admitted' : 'Saved' }, b);
      b.addEventListener('click', () => { $('library').close(); chooseCase(i); });
    });
  }

  /* ---------------- actions ---------------- */
  function chooseCase(i, keepClockAtEnd = true) {
    S.scrubbedStep = null;
    S.playing = false; S.batchPlaying = false;
    S.caseIndex = i; $('case-select').value = String(i);
    S.scenario = caseRec().family;
    S.clock = keepClockAtEnd ? traceEnd(traceFor()) : 0;
    renderWorkflow(); refreshInspector(); renderModel();
  }
  function setConfig(c) {
    S.scrubbedStep = null;
    S.config = c; $('config-select').value = c;
    S.playing = false; S.batchPlaying = false;
    S.clock = traceEnd(traceFor());
    renderWorkflow(); refreshInspector(); renderModel();
  }
  function pendingIndex() {
    return dataset().cases.findIndex(r => CONFIG_ORDER.some(c => !S.admitted.has(traceFor(c, r).id)));
  }
  function admitCurrentCase() {
    let changed = false;
    CONFIG_ORDER.forEach(c => { const id = traceFor(c).id; if (!S.admitted.has(id)) { S.admitted.add(id); changed = true; } });
    if (changed) analyze();
  }
  function togglePlay() {
    S.scrubbedStep = null;
    S.batchPlaying = false;
    if (S.clock >= traceEnd(traceFor())) S.clock = 0;
    S.playing = !S.playing; S.lastT = performance.now();
    pushPlayback(); updatePlayButton();
  }
  function replay() {
    S.scrubbedStep = null;
    S.batchPlaying = false; S.clock = 0; S.playing = true; S.lastT = performance.now();
    pushPlayback(); updatePlayButton();
  }

  function tick(now) {
    if (S.playing) {
      const dt = Math.min(100, now - S.lastT) * Number($('speed').value);
      S.clock += dt;
      const end = traceEnd(traceFor());
      if (S.clock >= end) {
        S.clock = end; S.playing = false;
        const cont = S.batchPlaying;
        admitCurrentCase();
        const next = pendingIndex();
        if (cont && next >= 0) {
          S.caseIndex = next; $('case-select').value = String(next); S.scenario = caseRec().family;
          S.clock = 0; S.playing = true; S.batchPlaying = true;
        } else S.batchPlaying = false;
        renderWorkflow(); refreshInspector();
      } else pushPlayback();
      updatePlayButton();
    }
    S.lastT = now;
    requestAnimationFrame(tick);
  }

  function setView(name) {
    S.view = name;
    for (const n of ['workflow', 'model']) {
      $('view-' + n).hidden = n !== name;
      $('tab-' + n).setAttribute('aria-selected', n === name ? 'true' : 'false');
      $('tab-' + n).tabIndex = n === name ? 0 : -1;
    }
    document.body.dataset.view = name;
    if (S.inspector) closeInspector();
    if (name !== 'model' && walkStage !== null) { walkStage = null; model.setStage(null); $('walk').hidden = true; document.querySelector('.model-wrap').classList.remove('walking'); }
    $('library-btn').hidden = name !== 'workflow';
  }

  function start() {
    S.scrubbedStep = null;
    if (S.inspector) closeInspector();
    if (walkStage !== null) setWalk(null);
    S.weights = Object.assign({}, S.bundle.default_weights);
    S.analysis = null; S.analysisMode = 'none'; S.analysisStale = false;
    S.admitted = new Set();
    S.playing = false; S.batchPlaying = false;
    let i = dataset().cases.findIndex(r => dataset().traces.some(t => t.case_id === r.id && t.config === 'none' && t.outcome.unauthorized));
    S.caseIndex = Math.max(0, i);
    S.scenario = caseRec().family;
    fillCases();
    S.clock = traceEnd(traceFor());
    renderWorkflow();
    provenance();
    renderModel();
    analyze();
  }

  function provenance() {
    const p = $('provenance'), b = S.bundle;
    const n = { heldout: '60 held-out cases, ten per scenario', development: '12 separate development cases', walkthrough: '3 curated examples, excluded from evaluation', recorded: '3 archived real-model cases' }[S.split];
    p.textContent = `${b.plan.version} · policy ${b.plan.policy} · ${n}. ${S.split === 'recorded' ? b.recorded.notice : b.plan.sampling} Plan digest ${b.plan_digest.slice(0, 12)}…, held-out evidence digest ${b.evidence_digest.slice(0, 12)}….`;
  }

  /* ---------------- wiring ---------------- */
  function wire() {
    $('case-select').addEventListener('change', e => chooseCase(Number(e.target.value)));
    $('config-select').addEventListener('change', e => setConfig(e.target.value));
    $('play').addEventListener('click', togglePlay);
    $('replay').addEventListener('click', replay);
    reduceMQ.addEventListener('change', () => pushPlayback());

    for (const n of ['workflow', 'model']) {
      $('tab-' + n).addEventListener('click', () => setView(n));
      $('tab-' + n).addEventListener('keydown', e => {
        if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) {
          e.preventDefault();
          const next = e.key === 'Home' ? 'workflow' : e.key === 'End' ? 'model' : n === 'workflow' ? 'model' : 'workflow';
          setView(next); $('tab-' + next).focus();
        }
      });
    }

    $('insp-close').addEventListener('click', closeInspector);
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && S.inspector && !document.querySelector('dialog[open]')) { e.preventDefault(); closeInspector(); }
    });

    ['evidence-btn', 'model-evidence-btn'].forEach(id => $(id).addEventListener('click', () => { renderEvidence(); $('evidence').showModal(); }));
    $('play-batch').addEventListener('click', () => {
      S.scrubbedStep = null;
      if (S.batchPlaying) { S.batchPlaying = false; S.playing = false; }
      else {
        const next = pendingIndex(); if (next < 0) return;
        S.caseIndex = next; $('case-select').value = String(next); S.scenario = caseRec().family;
        S.clock = 0; S.batchPlaying = true; S.playing = true; S.lastT = performance.now();
        $('evidence').close();
      }
      renderWorkflow();
    });
    $('complete-batch').addEventListener('click', () => {
      S.scrubbedStep = null;
      S.playing = false; S.batchPlaying = false;
      dataset().traces.forEach(t => S.admitted.add(t.id));
      S.clock = traceEnd(traceFor());
      renderWorkflow(); analyze();
    });

    $('library-btn').addEventListener('click', () => { renderLibrary(); $('library').showModal(); });
    $('ex-unsafe').addEventListener('click', () => {
      const i = dataset().cases.findIndex(r => dataset().traces.some(t => t.case_id === r.id && t.config === 'none' && t.outcome.unauthorized));
      if (i < 0) { banner('This evidence set has no saved unauthorized-payment example.'); return; }
      $('library').close(); S.config = 'none'; $('config-select').value = 'none'; chooseCase(i);
    });
    $('ex-legit').addEventListener('click', () => {
      let i = dataset().cases.findIndex(r => { const ts = dataset().traces.filter(t => t.case_id === r.id); return ts.some(t => t.config === 'none' && t.outcome.legitimate_completed) && ts.some(t => t.config === 'reviewer' && !t.outcome.legitimate_completed); });
      if (i < 0) i = dataset().cases.findIndex(r => dataset().traces.some(t => t.case_id === r.id && t.outcome.legitimate_completed));
      if (i < 0) { banner('No legitimate-completion example in this evidence set.'); return; }
      $('library').close(); S.config = 'reviewer'; $('config-select').value = 'reviewer'; chooseCase(i);
    });
    $('ex-service').addEventListener('click', () => {
      $('library').close();
      S.split = 'walkthrough'; $('dataset').value = 'walkthrough';
      start(); setConfig('reviewer'); chooseCase(0);
    });

    $('setup-btn').addEventListener('click', () => {
      $('dataset').value = S.split; $('prior-a').value = S.prior.a; $('prior-b').value = S.prior.b;
      $('setup').showModal();
    });
    $('setup-close').addEventListener('click', () => $('setup').close());
    $('setup-form').addEventListener('submit', e => {
      e.preventDefault();
      const a = Number($('prior-a').value), b = Number($('prior-b').value);
      if (!(a > 0 && a <= 100 && b > 0 && b <= 100)) { banner('Prior parameters must be positive and at most 100. Setup unchanged.'); return; }
      S.split = $('dataset').value; S.prior = { a, b };
      $('setup').close(); banner(''); start();
    });

    $('weights-btn').addEventListener('click', openWeights);
    $('weights-close').addEventListener('click', () => $('weights').close());
    $('weights-reset').addEventListener('click', () => { S.weights = Object.assign({}, S.bundle.default_weights); renderWeightRows(); $('weight-error').textContent = ''; analyze(); });
    $('weights-form').addEventListener('submit', e => {
      e.preventDefault();
      const draft = {}; let bad = false;
      SCENARIO_ORDER.forEach(sc => { const v = $('w-' + sc).value.trim(); const w = Number(v) / 100; if (v === '' || !Number.isFinite(w) || w < 0) bad = true; draft[sc] = w; });
      const tot = Object.values(draft).reduce((x, y) => x + y, 0);
      if (bad || Math.abs(tot - 1) > 1e-9) { $('weight-error').textContent = 'Enter six nonnegative percentages totaling 100%. The current projection is unchanged.'; return; }
      $('weight-error').textContent = '';
      S.weights = draft; $('weights').close(); analyze();
    });
    $('table-btn').addEventListener('click', () => $('table').showModal());
    $('walk-btn').addEventListener('click', () => { if (S.inspector) closeInspector(); setWalk(0); $('walk-title').focus({ preventScroll: true }); });
    $('walk-next').addEventListener('click', () => setWalk(walkStage >= 4 ? null : walkStage + 1));
    $('walk-prev').addEventListener('click', () => setWalk(Math.max(0, walkStage - 1)));
    $('walk-close').addEventListener('click', () => setWalk(null));
    document.addEventListener('keydown', e => {
      if (walkStage === null || document.querySelector('dialog[open]')) return;
      if (e.key === 'Escape' && !S.inspector) { e.preventDefault(); setWalk(null); }
    });
    $('checks-btn').addEventListener('click', () => { $('model-checks').showModal(); loadDiagnostics(); });
    $('methods-btn').addEventListener('click', () => $('methods').showModal());
  }

  function openWeights() { renderWeightRows(); $('weight-error').textContent = ''; $('weights').showModal(); }

  /* ---------------- boot ---------------- */
  async function boot() {
    topo = V.mountTopology($('topology'), {
      onNodeSelect: (vid) => { openInspector('node', vid, document.querySelector(`#topology [data-node="${vid}"]`)); },
    });
    model = V.mountModel($('model'), {
      onScenarioSelect: sc => { S.scenario = sc; renderModel(); openInspector('scenario', sc, document.querySelector(`#model [data-scenario="${sc}"]`)); },
      onWeightsOpen: openWeights,
    });
    document.querySelectorAll('button, select, input').forEach(control => { control.disabled = true; });
    wire();
    try {
      S.bundle = await loadBundle();
      fillSelectors();
      setView('workflow');
      start();
      document.querySelectorAll('button, select, input').forEach(control => { control.disabled = false; });
      $('loading').hidden = true;
      requestAnimationFrame(t => { S.lastT = t; requestAnimationFrame(tick); });
    } catch (e) {
      $('loading').hidden = true;
      banner('Saved evidence could not be loaded: ' + e.message + '. Refresh to retry.');
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
