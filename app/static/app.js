"use strict";
const $ = (id) => document.getElementById(id);
let snapshot, config, running = false, operatorToken = "", noticeTimer;
const money = (x) => new Intl.NumberFormat("en-US", {style:"currency", currency:"USD", maximumFractionDigits:2}).format(x);
const escapeText = (x) => String(x ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const title = (x) => String(x).replaceAll("_", " ").replace(/^\w/, c => c.toUpperCase());
function notice(message) { $("notice").textContent = message; $("notice").classList.remove("hidden"); clearTimeout(noticeTimer); noticeTimer = setTimeout(() => $("notice").classList.add("hidden"), 8000); }
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:"POST",headers:{"Content-Type":"application/json", "X-Operator-Token":operatorToken},body:JSON.stringify(body)});
  if (!response.ok) { let error; try {error = await response.json();} catch {error = {};} throw new Error(typeof error.detail === "string" ? error.detail : `Request failed (${response.status}). Check inputs and try again.`); }
  return response.json();
}
function showView(view) {
  document.querySelectorAll(".view").forEach(v => v.classList.toggle("hidden", v.id !== `view-${view}`));
  document.querySelectorAll(".nav-item").forEach(v => v.classList.toggle("active", v.dataset.view === view));
  $("crumb").textContent = {overview:"Overview",events:"Decision ledger",methods:"Risk methodology",connections:"Connections"}[view];
}
document.querySelectorAll("[data-view]").forEach(b => b.addEventListener("click", () => showView(b.dataset.view)));
function chart(gross, residual) {
  const width = 600, left = 99, right = 552, max = Math.max(5, gross.expected_loss_ci95[1], residual.expected_loss_ci95[1]) * 1.15;
  const x = v => left + (right-left) * v / max;
  let lines = "";
  for(let i=0;i<=4;i++) {const value=max*i/4; lines += `<line class="chart-grid" x1="${x(value)}" x2="${x(value)}" y1="24" y2="163"/><text class="axis-label" text-anchor="middle" x="${x(value)}" y="189">$${value.toFixed(0)}</text>`;}
  [[gross,69,"#e77950","Proposed"],[residual,132,"#438778","Monitored"]].forEach(([r,y,color,label]) => {
    const [lo,hi]=r.expected_loss_ci95;
    lines += `<text class="chart-label" x="8" y="${y+4}">${label}</text><line x1="${x(lo)}" x2="${x(hi)}" y1="${y}" y2="${y}" stroke="${color}" stroke-opacity="0.16" stroke-width="24" stroke-linecap="round"/><line x1="${x(lo)}" x2="${x(hi)}" y1="${y}" y2="${y}" stroke="${color}" stroke-width="1.5"/><line x1="${x(lo)}" x2="${x(lo)}" y1="${y-5}" y2="${y+5}" stroke="${color}"/><line x1="${x(hi)}" x2="${x(hi)}" y1="${y-5}" y2="${y+5}" stroke="${color}"/><circle cx="${x(r.expected_loss_usd)}" cy="${y}" r="6" fill="${color}" stroke="white" stroke-width="2"/><text class="axis-label" x="${x(r.expected_loss_usd)}" y="${y-22}" text-anchor="middle">${money(r.expected_loss_usd)}</text>`;
  });
  $("risk-chart").innerHTML = `<svg viewBox="0 0 ${width} 208" role="img" aria-label="Proposed mean ${money(gross.expected_loss_usd)}; monitored mean ${money(residual.expected_loss_usd)}; bands show 95 percent posterior uncertainty">${lines}</svg>`;
}
function rows(events) {
  if (!events.length) return '<tr><td colspan="6" class="empty">No decisions yet. Start an evaluation to collect evidence.</td></tr>';
  return events.map(e => `<tr><td><span class="case-name">${escapeText(e.case.id)}</span><small>${escapeText(e.case.order.id)}</small></td><td><span class="scenario">${escapeText(title(e.case.category))}</span></td><td>${escapeText(title(e.proposal.action))} ${e.proposal.action === "refund" ? money(e.proposal.amount_cents/100) : ""}</td><td><span class="tag ${e.monitor.allowed ? "green" : "orange"}">${e.monitor.allowed ? "Allowed" : "Blocked"}</span></td><td class="${e.gross_loss_cents ? "positive" : ""}">${money(e.gross_loss_cents/100)}</td><td><button class="row-button" data-event="${escapeText(e.id)}" aria-label="Inspect ${escapeText(e.case.id)}">↗</button></td></tr>`).join("");
}
function renderRows() {
  if(!snapshot) return;
  $("recent-events").innerHTML = rows(snapshot.events.slice(-5).reverse());
  const filter = $("filter").value;
  $("all-events").innerHTML = rows(snapshot.events.filter(e => filter === "all" || (filter === "allowed") === e.monitor.allowed).slice().reverse());
}
function render() {
  const s=snapshot, g=s.gross, r=s.residual;
  $("gross-mean").textContent = money(g.expected_loss_usd);
  $("residual-mean").textContent = money(r.expected_loss_usd);
  for (const [name, value] of [["gross",g],["residual",r]]) $(`${name}-ci`).textContent = `${money(value.expected_loss_ci95[0])} – ${money(value.expected_loss_ci95[1])} · 95% credible`;
  $("prevented").textContent = money(s.prevented_usd);
  $("blocked-label").textContent = `${s.blocked} blocked proposals · ${money(r.observed_loss_usd)} residual harm observed`;
  $("n").textContent = `${g.n} / ${s.run.count}`;
  $("failures-label").textContent = `${g.failures} harmful proposals · ${(100*g.frequency_mean).toFixed(1)}% posterior frequency`;
  $("sample-tag").textContent = g.n === 0 ? "Prior only" : g.failures < 5 ? "Sparse failures" : "Synthetic evidence";
  $("run-label").textContent = s.run.mode === "offline" ? "Offline fixture evaluation" : "Claude API evaluation";
  $("run-meta").textContent = `Seed ${s.run.seed} · ${s.run.status.replaceAll("_"," ")} · memory ${s.run.use_memory ? "on" : "off"}${s.run.mode === "claude" ? ` · ${s.tokens.input_tokens} in / ${s.tokens.output_tokens} out tokens` : ""}`;
  $("bound-value").textContent = r.anytime_upper_usd === null ? "Sequential bound disabled for adaptive memory" : `Residual mean ≤ ${money(r.anytime_upper_usd)} · 95% anytime upper bound`;
  $("bound-note").textContent = r.anytime_upper_usd === null ? "Bayesian intervals describe a stationary approximation." : "Bounded loss ≤ $1,000, common mean assumption · conservative at small n.";
  const d=s.drift;
  $("drift-status").textContent = d.alert ? `Reference-rate alert · max e-value ${d.max_e_value.toFixed(1)} ≥ 20. Proposed harm exceeds the 10% reference.` : `Reference-rate signal · e-value ${d.e_value.toFixed(2)} / 20 · no threshold crossing.`;
  $("drift-status").classList.toggle("alert",d.alert);
  $("open-run").textContent = running ? "Ⅱ Pause after this case" : g.n < s.run.count ? "▶ Continue evaluation" : "＋ New evaluation";
  $("open-run").classList.toggle("running", running);
  chart(g,r); renderRows();
}
function eventDetail(eventId) {
  const e=snapshot.events.find(e => e.id === eventId); if(!e) return;
  $("detail-title").textContent = `${e.case.id} · ${title(e.case.category)}`;
  $("event-detail").innerHTML = `<div class="detail-card"><h3>Trusted order state</h3><div class="detail-grid"><div>Paid<strong>${money(e.case.order.paid_cents/100)}</strong></div><div>Age<strong>${e.case.order.age_days} days</strong></div><div>Customer<strong>${escapeText(e.case.customer)}</strong></div><div>Owner<strong>${escapeText(e.case.order.owner)}</strong></div><div>Previously refunded<strong>${money(e.case.order.refunded_cents/100)}</strong></div><div>Requested<strong>${money(e.case.requested_cents/100)}</strong></div></div></div><div class="detail-card"><h3>Untrusted customer message</h3>${escapeText(e.case.message)}</div><div class="detail-card"><h3>Agent proposal</h3><strong>${escapeText(title(e.proposal.action))} · ${money(e.proposal.amount_cents/100)}</strong><p>${escapeText(e.proposal.reason)}</p></div><div class="detail-card"><h3>Independent monitor</h3><strong>${e.monitor.allowed ? "Allowed" : "Blocked"}</strong><p>${e.monitor.rules.length ? e.monitor.rules.map(x=>escapeText(title(x))).join(" · ") : "All policy checks passed"}</p><div class="detail-grid"><div>Proposed harm<strong>${money(e.gross_loss_cents/100)}</strong></div><div>Executed<strong>${money(e.executed_cents/100)}</strong></div><div>Residual harm<strong>${money(e.residual_loss_cents/100)}</strong></div><div>Prevented harm<strong>${money(e.prevented_loss_cents/100)}</strong></div></div></div><div class="detail-card"><h3>Memory provenance</h3>${escapeText(title(e.memory.status))} · ${e.memory.hits.length} recalled hits${e.memory.write_status ? `<p>${escapeText(title(e.memory.write_status))}</p>` : ""}${e.memory.recall_trace_id ? `<p>Trace: ${escapeText(e.memory.recall_trace_id)}</p>` : ""}${e.memory.hits.map(h=>`<p>${escapeText(h.text)}</p>`).join("")}</div><div class="detail-card"><h3>Audit identity</h3>${escapeText(e.id)}<br>${escapeText(e.at)}<br>Policy: ${escapeText(e.monitor.policy_version)}</div>`;
  $("event-dialog").showModal();
}
document.addEventListener("click",e=>{const b=e.target.closest("[data-event]");if(b)eventDetail(b.dataset.event);});
$("filter").addEventListener("change",renderRows);
$("close-event").addEventListener("click",()=>$("event-dialog").close());
$("close-run").addEventListener("click",()=>$("run-dialog").close());
async function history() {
  const runs=await api("/api/runs");
  $("run-select").innerHTML=runs.map(r=>`<option value="${escapeText(r.id)}">${escapeText(r.mode === "offline" ? "Offline" : "Claude")} · seed ${r.seed} · ${escapeText(r.status)}</option>`).join("");
  if(snapshot) $("run-select").value=snapshot.run.id;
  return runs;
}
$("run-select").addEventListener("change", async () => {if(running){notice("Pause the current evaluation before switching runs.");$("run-select").value=snapshot.run.id;return;}try{snapshot=await api(`/api/runs/${$("run-select").value}`);render();}catch(e){notice(e.message);}});
async function advance() {
  running=true;render();
  while(running && snapshot.events.length < snapshot.run.count) {
    try {snapshot=await api(`/api/runs/${snapshot.run.id}/step`, {expected_seq:snapshot.events.length});render();}
    catch(e){notice(e.message);break;}
    await new Promise(resolve=>setTimeout(resolve,120));
  }
  running=false;render();await history();
}
$("open-run").addEventListener("click",()=>{
  if(running){running=false;render();return;}
  if(snapshot && snapshot.events.length < snapshot.run.count){advance().catch(e=>notice(e.message));return;}
  $("run-dialog").showModal();
});
$("mode").addEventListener("change",()=>{$("count").max=$("mode").value==="claude"?40:200;if(Number($("count").value)>Number($("count").max))$("count").value=$("count").max;});
$("run-form").addEventListener("submit",async e=>{
  e.preventDefault();
  const submit=e.submitter;submit.disabled=true;
  try {
    snapshot=await api("/api/runs",{seed:Number($("seed").value),count:Number($("count").value),mode:$("mode").value,use_memory:$("use-memory").checked});
    $("run-dialog").close();showView("overview");render();await history();await advance();
  }catch(error){notice(error.message);}finally{submit.disabled=false;}
});
$("export").addEventListener("click",()=>{if(snapshot)window.location.href=`/api/runs/${snapshot.run.id}/export`;});
$("save-token").addEventListener("click",()=>{operatorToken=$("operator-token").value;$("operator-token").value="";$("token-state").textContent=operatorToken?"Token held for this tab. It will be sent only to this app's server.":"Token cleared.";});
async function init(){
  config=await api("/api/config");
  $("anthropic-status").textContent=config.anthropic_configured ? `Server key configured · ${config.model}. ${config.live_enabled ? "Live runs available with operator access." : "Set an operator token to enable live evaluations."} Workspace attempt budget: ${config.claude_attempts_used} / ${config.claude_attempts_limit}.` : "Not connected · offline demo ready.";
  $("surreal-status").textContent=config.surreal_configured ? "Agent Memory configured. Run a memory evaluation to verify recall and storage." : "Not connected · local memory demo available.";
  $("mode").options[1].disabled=!config.live_enabled;
  const runs=await history();
  if(runs.length){snapshot=await api(`/api/runs/${runs[0].id}`);render();}else{$("run-label").textContent="No evaluations yet";}
}
init().catch(e=>notice(`Could not load dashboard: ${e.message}`));
