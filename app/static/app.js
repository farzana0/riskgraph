"use strict";
const $ = id => document.getElementById(id);
const money = value => new Intl.NumberFormat("en-US", {style:"currency",currency:"USD",maximumFractionDigits:2}).format(value);
const integer = value => new Intl.NumberFormat("en-US").format(value);
const escapeText = value => String(value ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const title = value => String(value ?? "").replaceAll("_"," ").replace(/^\w/,c=>c.toUpperCase());
let snapshot, config, running=false, pauseRequested=false, operatorToken="", operatorVerified=false, noticeTimer, benchmarksLoaded=false;
const scenarioName = key => config?.scenario_labels?.[key] || title(key);
const svgIcon = name => `<svg class="icon" aria-hidden="true"><use href="#i-${name}"></use></svg>`;
function notice(message) {
  if($("run-dialog").open){$("run-error").textContent=message;$("run-error").classList.remove("hidden");}
  $("notice").textContent=message;$("notice").classList.remove("hidden");clearTimeout(noticeTimer);
  noticeTimer=setTimeout(()=>$("notice").classList.add("hidden"),10000);
}
async function api(path,body) {
  const response=await fetch(path,body===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json","X-Operator-Token":operatorToken},body:JSON.stringify(body)});
  if(!response.ok){let detail={};try{detail=await response.json();}catch{} const error=new Error(typeof detail.detail==="string"?detail.detail:`Request failed (${response.status}). Check the evaluation settings.`);error.status=response.status;throw error;}
  return response.json();
}
function accessState(){
  $("access-badge").textContent=operatorVerified?"Evaluation access":config?.operator_token_required?"View only":"Local environment";
  $("access-badge").classList.toggle("authorized",operatorVerified);
  $("forget-token").classList.toggle("hidden",!operatorVerified);
  $("new-from-access").classList.toggle("hidden",!operatorVerified);
  $("operator-entry").classList.toggle("hidden",operatorVerified);
}
function showView(view){
  document.querySelectorAll(".view").forEach(v=>v.classList.toggle("hidden",v.id!==`view-${view}`));
  document.querySelectorAll(".nav-item").forEach(v=>{v.classList.toggle("active",v.dataset.view===view);if(v.dataset.view===view)v.setAttribute("aria-current","page");else v.removeAttribute("aria-current");});
  $("crumb").textContent={overview:"Risk overview",events:"Decisions",validation:"Stress tests",methods:"How it works",connections:"Connections"}[view];
  if(view==="validation"&&!benchmarksLoaded){loadBenchmarks();loadStress();}
}
document.querySelectorAll("[data-view]").forEach(button=>button.addEventListener("click",()=>showView(button.dataset.view)));
function chart(gross,residual){
  const max=Math.max(5,gross.expected_loss_ci95[1],residual.expected_loss_ci95[1])*1.15;
  const left=100,right=550,x=value=>left+(right-left)*value/max;
  let lines="";
  for(let i=0;i<=4;i++){const value=max*i/4;lines+=`<line class="chart-grid" x1="${x(value)}" x2="${x(value)}" y1="20" y2="160"/><text class="axis-label" text-anchor="middle" x="${x(value)}" y="188">$${value.toFixed(0)}</text>`;}
  [[gross,65,"#bd6242","Proposed"],[residual,132,"#216b5b","Monitored"]].forEach(([risk,y,color,label])=>{
    const [lo,hi]=risk.expected_loss_ci95;
    lines+=`<text class="chart-label" x="8" y="${y+4}">${label}</text><line x1="${x(lo)}" x2="${x(hi)}" y1="${y}" y2="${y}" stroke="${color}" stroke-opacity=".13" stroke-width="24" stroke-linecap="round"/><line x1="${x(lo)}" x2="${x(hi)}" y1="${y}" y2="${y}" stroke="${color}" stroke-width="1.7"/><circle cx="${x(risk.expected_loss_usd)}" cy="${y}" r="6" fill="${color}" stroke="white" stroke-width="2"/><text class="axis-label" x="${x(risk.expected_loss_usd)}" y="${y-22}" text-anchor="middle">${money(risk.expected_loss_usd)}</text>`;
  });
  $("risk-chart").innerHTML=`<svg viewBox="0 0 600 205" role="img" aria-label="Bayesian mean binned loss: proposed ${money(gross.expected_loss_usd)}, residual ${money(residual.expected_loss_usd)}. Bands show 95 percent credible intervals, separate from confidence bounds.">${lines}</svg>`;
}
function rows(events){
  if(!events.length)return '<tr><td colspan="6" class="empty">No matching decisions. Adjust the filters or start an evaluation.</td></tr>';
  return events.map(event=>`<tr><td><span class="case-name">${escapeText(event.case.id)}</span><small>${escapeText(event.case.order.id)}</small></td><td>${escapeText(scenarioName(event.case.category))}</td><td>${escapeText(title(event.proposal.action))}${event.proposal.action==="refund"?` ${money(event.proposal.amount_cents/100)}`:""}</td><td><span class="tag ${event.monitor.allowed?"green":"orange"}">${event.monitor.allowed?"Allowed":"Blocked"}</span></td><td class="${event.gross_loss_cents?"positive":""}">${money(event.gross_loss_cents/100)}</td><td><button class="row-button" data-event="${escapeText(event.id)}" aria-label="Inspect ${escapeText(event.case.id)}">View decision</button></td></tr>`).join("");
}
function renderRows(){
  if(!snapshot)return;
  $("recent-events").innerHTML=rows(snapshot.events.slice(-5).reverse());
  const filter=$("filter").value,query=$("search").value.trim().toLowerCase();
  const events=snapshot.events.filter(event=>(filter==="all"||(filter==="allowed")===event.monitor.allowed)&&(!query||[event.case.id,event.case.order.id,event.case.category,scenarioName(event.case.category),event.proposal.action,...event.monitor.rules,...event.monitor.rules.map(title)].join(" ").toLowerCase().includes(query))).slice().reverse();
  $("all-events").innerHTML=rows(events);$("results-count").textContent=`${events.length} of ${snapshot.events.length} decisions`;
}
function render(){
  if(!snapshot)return;
  const s=snapshot,g=s.gross,r=s.residual,d=s.drift;
  const archived=g.n<s.run.count&&(s.resume_supported===false||s.run.framework!=="proposal_review_gate_v2");
  for(const [name,risk] of [["gross",g],["residual",r]]){
    $(`${name}-mean`).textContent=g.n===0?"—":risk.anytime_upper_usd===null?money(risk.observed_loss_usd/g.n):money(risk.anytime_upper_usd);
    $(`${name}-mean`).classList.remove("unavailable");
    $(`${name}-ci`).textContent=g.n===0?"Awaiting decisions":risk.anytime_upper_usd===null?"Observed average · no confidence bound":"Upper confidence bound";
  }
  $("exposure-title").textContent=r.anytime_upper_usd===null?"What did this test put at risk?":"How much risk remains?";
  $("exposure-description").textContent=r.anytime_upper_usd===null?"Observed average loss per decision. Descriptive, not a forecast.":"A conservative upper estimate of average loss per decision.";
  $("proposed-loss").textContent=money(g.observed_loss_usd);
  $("prevented").textContent=money(s.prevented_usd);
  $("blocked-label").textContent=`${s.blocked} total control stops · excludes permitted declines`;
  $("n").textContent=`${g.n} / ${s.run.count}`;
  $("failures-label").textContent=`${g.failures} proposed payments could cause loss`;
  $("sample-tag").textContent=g.n===0?"Awaiting evidence":g.n<100?"Limited evidence":"Synthetic evidence";
  $("quality-label").textContent=g.n<100?"Small sample":"Scenario-specific results";
  $("run-label").textContent=s.run.mode==="offline"?(s.run.prompt_version==="injected-failures-v2"?"Stress agent · injected failures":"Demo agent · deliberately naive"):"Claude · live AI evaluation";
  $("run-meta").textContent=`Seed ${s.run.seed} · memory ${s.run.use_memory?"on":"off"}${s.run.mode==="claude"?` · ${integer(s.tokens.input_tokens)} input / ${integer(s.tokens.output_tokens)} output tokens`:""}`;
  $("run-status").textContent=archived?"Archived":running?"Running":s.run.status==="running"?"Paused":title(s.run.status);
  $("run-progress").max=s.run.count;$("run-progress").value=g.n;$("progress-label").textContent=`${g.n} of ${s.run.count} assessed`;
  const titleText=archived?"Earlier evaluation preserved":g.n===0?"Ready to review risk":r.observed_loss_usd>0?"Loss occurred after controls":d.alert?"Increased risky activity detected":"No loss occurred after controls";
  $("assessment-title").textContent=titleText;
  $("assessment-description").textContent=g.n===0?"Start the evaluation to assess proposals against trusted policy.":r.anytime_upper_usd===null?"This is an adaptive or designed stress test. Review observed results; a stationary loss bound is not shown.":`${g.n} decisions were reviewed. A small sample cannot rule out rare or costly failures.`;
  if(archived)$("assessment-description").textContent="Start a new evaluation to use the revised workflow. Existing evidence remains available for inspection and export.";
  $("assessment-description").textContent=r.observed_loss_usd>0?"Inspect executed decisions and policy checks before drawing conclusions.":$("assessment-description").textContent;
  if(s.run.mode==="offline"&&s.run.prompt_version==="injected-failures-v2"&&g.n>0){
    $("assessment-title").textContent=r.observed_loss_usd>0?"Injected failures caused simulated loss":"Control demonstration · injected mistakes stopped";
    $("assessment-description").textContent="Deliberately unsafe proposals create loss at risk before controls. Stopped amounts are simulated exposure, not real money saved.";
  }
  document.querySelector(".assessment").classList.toggle("attention",d.alert||r.observed_loss_usd>0);
  $("bound-value").textContent=r.anytime_upper_usd===null?"Conservative bound not available for this test":g.n===0?"Collect evidence to estimate remaining risk":`Average loss after controls: no more than ${money(r.anytime_upper_usd)} per decision`;
  $("bound-note").textContent=r.anytime_upper_usd===null?"Adaptive memory, designed catalogues, workload shifts, and correlated suites do not meet the fixed-tail assumptions.":"Each upper bound has 97.5% time-uniform coverage; both together have at least 95% coverage within this evaluation, under fixed conditional loss-tail probabilities and a $1,000 loss cap. This is a bound on average loss, not the maximum possible single loss or an insurance premium.";
  const evidence=d.max_e_value<100?d.max_e_value.toFixed(2):d.max_e_value.toExponential(1);
  $("drift-status").textContent=d.alert?`Monitoring alert: evidence suggests more than the 10% reference rate of harmful proposals. Review the decisions.`:"No monitoring alert. This does not establish that the agent is safe.";
  $("drift-status").classList.toggle("alert",d.alert);
  $("continue-run").textContent=running?(pauseRequested?"Pausing…":"Ⅱ Pause after this case"):"▶ Continue evaluation";
  $("continue-run").disabled=pauseRequested;
  $("continue-run").classList.toggle("hidden",!running&&(g.n>=s.run.count||archived));$("continue-run").classList.toggle("running",running);
  $("open-run").disabled=running;$("verify-evidence").disabled=running||!g.n;
  $("evaluation-error").textContent=s.run.error||"";$("evaluation-error").classList.toggle("hidden",!s.run.error);
  const counts=s.scenario_summary||s.events.reduce((all,e)=>(all[e.case.category]=(all[e.case.category]||0)+1,all),{});
  $("scenario-coverage").innerHTML=Object.entries(counts).map(([name,count])=>`<span class="coverage-chip">${svgIcon("shield")}${escapeText(scenarioName(name))}<b>${count}</b></span>`).join("")||'<p class="form-help">Scenario coverage appears as cases are assessed.</p>';
  $("suite-label").textContent=config?.suites?.[s.run.suite]||"Original mixed workload";
  $("plain-bound-note").textContent=r.anytime_upper_usd===null?"The test intentionally changes conditions or uses memory. Observed outcomes remain available, but the fixed-distribution confidence guarantee does not apply.":g.n===0?"Start an evaluation to collect evidence.":"No observed loss does not mean no risk. The upper estimate stays cautious when the sample is small.";
  $("evidence-heading").textContent=g.n<100?"Limited evidence":"Synthetic evidence only";
  $("evidence-note").textContent=`${g.n} decisions across ${Object.keys(counts).length} scenario types. Results apply to this test, not all real-world requests.`;
  $("service-note").textContent=`${s.unnecessary_abstentions} fully eligible requests were not paid. These may be declines, referrals, or control stops; inspect decisions to assess service impact.`;
  $("observed-loss").textContent=money(r.observed_loss_usd);$("harmful-blocked").textContent=s.quality?.harmful_blocked??s.events.filter(e=>!e.monitor.allowed&&e.gross_loss_cents>0).length;
  $("protocol-blocked").textContent=s.quality?.protocol_rejections??s.events.filter(e=>!e.monitor.allowed&&!e.gross_loss_cents).length;
  $("estimate-details").innerHTML=[["Proposed",g],["Residual",r]].map(([label,risk])=>`<p><strong>${label} mean: ${money(risk.expected_loss_usd)}</strong><br>95% credible: ${money(risk.expected_loss_ci95[0])}–${money(risk.expected_loss_ci95[1])}${risk.prior_sensitivity_usd?`<br>Prior sensitivity of the mean: ${money(risk.prior_sensitivity_usd[0])}–${money(risk.prior_sensitivity_usd[1])}`:""}</p>`).join("");
  chart(g,r);renderRows();
}
function eventDetail(id){
  const e=snapshot.events.find(event=>event.id===id);if(!e)return;
  $("detail-title").textContent=`${e.case.id} · ${scenarioName(e.case.category)}`;
  const review=e.review;
  const checks=review?`<div class="detail-card"><h3>Policy review · recomputable evidence</h3><ul class="check-list">${review.checks.map(c=>`<li class="${!c.required?"not-required":c.passed?"passed":"failed"}"><span>${!c.required?"—":c.passed?"✓":"×"}</span>${escapeText(title(c.name))}${!c.required?" · not required":""}</li>`).join("")}</ul><p>Authorized refund limit: <strong>${money(review.authorized_limit_cents/100)}</strong>. The reviewer is read-only; the independent monitor controls execution.</p><details class="audit-identity"><summary>Evidence fingerprint and context sources</summary><code>${escapeText(review.evidence_sha256)}</code><p>Memory sources: ${review.memory_source_ids.map(escapeText).join(", ")||"None"}</p></details></div>`:"";
  $("event-detail").innerHTML=`<div class="trace-verdict"><span class="tag ${e.monitor.allowed?"green":"orange"}">${e.monitor.allowed?"Allowed":"Blocked"}</span><span>${e.gross_loss_cents?`${money(e.gross_loss_cents/100)} unauthorized proposed loss`:!e.monitor.allowed?"Protocol or policy rejection · no monetary harm scored":"No unauthorized monetary loss scored"}</span></div>${e.workflow?`<div class="trace-stages">${e.workflow.map(stage=>`<span>${escapeText(title(stage.role))} · ${escapeText(title(stage.status))}</span>`).join("")}</div>`:""}<div class="detail-card"><h3>Trusted order state</h3><div class="detail-grid"><div>Paid<strong>${money(e.case.order.paid_cents/100)}</strong></div><div>Age<strong>${e.case.order.age_days} days</strong></div><div>Requested<strong>${money(e.case.requested_cents/100)}</strong></div><div>Customer<strong>${escapeText(e.case.customer)}</strong></div><div>Owner<strong>${escapeText(e.case.order.owner)}</strong></div><div>Previously refunded<strong>${money(e.case.order.refunded_cents/100)}</strong></div></div></div><div class="detail-card"><h3>Untrusted customer message</h3>${escapeText(e.case.message)}</div><div class="detail-card"><h3>Agent proposal</h3><strong>${escapeText(title(e.proposal.action))} · ${money(e.proposal.amount_cents/100)}</strong><p>${escapeText(e.proposal.reason)}</p></div>${checks}<div class="detail-card"><h3>Independent monitor & execution</h3><p>${e.monitor.rules.length?e.monitor.rules.map(rule=>escapeText(title(rule))).join(" · "):"All required policy checks passed"}</p><div class="detail-grid"><div>Executed<strong>${money(e.executed_cents/100)}</strong></div><div>Residual harm<strong>${money(e.residual_loss_cents/100)}</strong></div><div>Prevented harm<strong>${money(e.prevented_loss_cents/100)}</strong></div></div></div><div class="detail-card"><h3>Incident memory</h3><p>${escapeText(title(e.memory.status))} · ${e.memory.hits.length} recalled sources</p>${e.memory.write_status?`<p>Storage: ${escapeText(title(e.memory.write_status))}</p>`:""}${e.memory.hits.map(hit=>`<p>${escapeText(hit.text)}</p>`).join("")}${e.memory.recall_error?`<p>${escapeText(e.memory.recall_error.message)}</p>`:""}${e.memory.write_error?`<p>${escapeText(e.memory.write_error.message)}</p>`:""}<details class="audit-identity"><summary>Memory provenance</summary><p>Retrieval trace: ${escapeText(e.memory.recall_trace_id||"None")}</p><p>Storage turn: ${escapeText(e.memory.turn_id||"None")}</p></details></div><details class="audit-identity"><summary>Audit identity</summary><code>${escapeText(e.id)}<br>${escapeText(e.at)}<br>Policy: ${escapeText(e.monitor.policy_version)}</code></details>`;
  $("event-dialog").showModal();
}
document.addEventListener("click",event=>{const button=event.target.closest("[data-event]");if(button)eventDetail(button.dataset.event);});
$("filter").addEventListener("change",renderRows);$("search").addEventListener("input",renderRows);
$("close-event").addEventListener("click",()=>$("event-dialog").close());
$("close-run").addEventListener("click",()=>$("run-dialog").close());
async function history(){
  const runs=await api("/api/runs");
  $("run-select").innerHTML=runs.map(run=>`<option value="${escapeText(run.id)}">${run.mode==="offline"?"Offline":"Claude"} · ${escapeText(config?.suites?.[run.suite]||"Original mixed workload")} · ${run.seed} · ${escapeText(title(run.status))}</option>`).join("");
  if(snapshot)$("run-select").value=snapshot.run.id;
  return runs;
}
$("run-select").addEventListener("change",async()=>{
  if(running){notice("Pause the evaluation before switching runs.");$("run-select").value=snapshot.run.id;return;}
  try{snapshot=await api(`/api/runs/${$("run-select").value}`);$("verification-result").textContent="";render();}catch(error){notice(error.message);}
});
async function advance(){
  running=true;pauseRequested=false;render();
  // A disconnected response may have committed on the server. Read the
  // persisted sequence before resuming; never blindly retry a paid proposal.
  try{snapshot=await api(`/api/runs/${snapshot.run.id}`);render();}
  catch(error){running=false;render();throw error;}
  while(running&&!pauseRequested&&snapshot.events.length<snapshot.run.count){
    try{snapshot=await api(`/api/runs/${snapshot.run.id}/step`,{expected_seq:snapshot.events.length});render();}
    catch(error){notice(error.message);try{snapshot=await api(`/api/runs/${snapshot.run.id}`);}catch{}break;}
    await new Promise(resolve=>setTimeout(resolve,100));
  }
  running=false;pauseRequested=false;render();await history();await refreshConfig();
}
function requireAccess(){
  if(config?.operator_token_required&&!operatorVerified){notice("Verify operator access in Connections before starting this evaluation.");return false;}
  return true;
}
$("continue-run").addEventListener("click",()=>{if(running){pauseRequested=true;render();return;}if(requireAccess())advance().catch(error=>notice(error.message));else showView("connections");});
$("open-run").addEventListener("click",()=>{$("run-error").classList.add("hidden");$("authorize-from-run").classList.add("hidden");const seed=new Uint32Array(1);crypto.getRandomValues(seed);$("seed").value=seed[0]%2147483648;updateRunSettings();$("run-dialog").showModal();});
function updateRunSettings(){
  const live=$("mode").value==="claude",max=live?40:200;
  $("count").max=max;if(Number($("count").value)>max)$("count").value=max;
  document.querySelectorAll("[data-count]").forEach(button=>{button.disabled=Number(button.dataset.count)>max;button.classList.toggle("selected",Number(button.dataset.count)===Number($("count").value));});
  const suite=$("suite").value;
  $("suite-help").textContent=config?.suite_descriptions?.[suite]||{balanced:"Everyday requests, policy limits, and adversarial cases.",adversarial:"Forged authority, prompt injection, ownership violations, and repeated refunds.",boundary:"Partial balances, day 29–31 requests, and amounts around the approval cap.",heavy_tail:"A 2% chance of a large request under the synthetic generator; short runs may contain none.",drift:"The workload changes halfway through the run. Stationary confidence bounds are disabled.",correlated:"Incidents arrive in groups of eight. Stationary confidence bounds are disabled.",baseline:"The original reproducible workload, retained for historical comparisons."}[suite];
  $("run-cost").textContent=live?`One Claude request per case · up to 40 cases per run. ${config?.claude_attempts_used??0} / ${config?.claude_attempts_limit??500} workspace attempts used.`:"Offline mode makes no model API requests.";
}
$("mode").addEventListener("change",updateRunSettings);$("suite").addEventListener("change",updateRunSettings);$("count").addEventListener("input",updateRunSettings);
document.querySelectorAll("[data-count]").forEach(button=>button.addEventListener("click",()=>{$("count").value=button.dataset.count;updateRunSettings();}));
$("authorize-from-run").addEventListener("click",()=>{$("run-dialog").close();showView("connections");$("operator-token").focus();});
$("run-form").addEventListener("submit",async event=>{
  event.preventDefault();if(!requireAccess()){$("authorize-from-run").classList.remove("hidden");return;}
  const submit=event.submitter||document.querySelector('#run-form button[type="submit"]');submit.disabled=true;
  try{snapshot=await api("/api/runs",{seed:Number($("seed").value),count:Number($("count").value),mode:$("mode").value,use_memory:$("use-memory").checked,suite:$("suite").value});$("run-dialog").close();$("verification-result").textContent="";showView("overview");render();await history();await advance();}
  catch(error){notice(error.message);}finally{submit.disabled=false;}
});
$("export").addEventListener("click",()=>{if(snapshot)window.location.href=`/api/runs/${snapshot.run.id}/export`;});
$("verify-evidence").addEventListener("click",async()=>{
  if(!snapshot)return;$("verify-evidence").disabled=true;
  try{const result=await api(`/api/runs/${snapshot.run.id}/verify`);$("verification-result").textContent=`${result.verified} recomputed reviews verified · ${result.mismatches} mismatches${result.legacy?` · ${result.legacy} earlier decisions have no review record`:""}. This verifies recorded policy evidence, not a formal proof of the agent.`;}
  catch(error){notice(error.message);}finally{$("verify-evidence").disabled=false;}
});
$("save-token").addEventListener("click",async()=>{
  operatorToken=$("operator-token").value.trim();if(!operatorToken){notice("Enter the configured operator token.");return;}
  $("save-token").disabled=true;$("token-state").textContent="Checking access…";
  try{await api("/api/operator/verify",{});operatorVerified=true;$("operator-token").value="";clearTimeout(noticeTimer);$("notice").classList.add("hidden");$("run-error").classList.add("hidden");$("token-state").textContent="Operator access verified. Evaluations are enabled in this tab.";accessState();}
  catch(error){operatorToken="";operatorVerified=false;$("token-state").textContent=error.message;accessState();}
  finally{$("save-token").disabled=false;}
});
$("new-from-access").addEventListener("click",()=>$("open-run").click());
$("forget-token").addEventListener("click",()=>{operatorToken="";operatorVerified=false;$("operator-token").value="";$("token-state").textContent="Access cleared for this tab.";accessState();});
async function loadBenchmarks(){
  try{
    const response=await api("/api/benchmarks");if(!response.available){$("benchmark-content").innerHTML='<p class="empty">Validation results are not included in this deployment.</p>';return;}
    const data=response.study,workflows=data.workflows.runs,total=workflows.reduce((sum,row)=>sum+row.cases,0)+data.workflows.poisoned_memory.cases;
    const comparisons=data.alarms.filter(row=>["moderate_015","moderate_020","shift_005_to_050"].includes(row.scenario));
    const comparisonHTML=comparisons.map(row=>{
      const name={moderate_015:"15% harmful proposals",moderate_020:"20% harmful proposals",shift_005_to_050:"5% → 50% mid-run shift"}[row.scenario];
      return `<div class="benchmark-row"><span>${name}</span>${["v1","v2"].map(version=>{const rate=row.versions[version].crossing_by_horizon["500"].rate*100;return `<div class="bar-label"><span>${version==="v1"?"Original alarm":"Mixture alarm"}</span><b>${rate.toFixed(1)}%</b></div><progress class="comparison-bar ${version==="v1"?"legacy":""}" max="100" value="${rate}" aria-label="${version} crossing rate ${rate.toFixed(1)} percent"></progress>`;}).join("")}</div>`;
    }).join("");
    const zero=data.zero_loss_bounds.find(row=>row.n===40),nullRow=data.alarms.find(row=>row.scenario==="null_010");
    $("benchmark-content").innerHTML=`<div class="benchmark-metrics"><article class="panel"><strong>${integer(data.policy.proposals)}</strong><p>Policy-stress proposals<br>${integer(data.policy.harmful_proposals)} harmful · ${data.policy.harmful_allowed} harmful bypasses</p></article><article class="panel"><strong>${integer(total)}</strong><p>End-to-end decisions<br>Seven suites and poisoned-memory stress</p></article><article class="panel"><strong>${(nullRow.versions.v2.crossing_by_horizon["500"].rate*100).toFixed(2)}%</strong><p>Null false-alarm rate<br>10% harm reference · ${integer(nullRow.trajectories)} trajectories</p></article></div><div class="benchmark-grid"><article class="panel"><h2>Broader alarm sensitivity</h2><p>Percentage of synthetic trajectories triggering by decision 500. Each comparison uses the same outcomes for both versions.</p>${comparisonHTML}</article><article class="panel"><h2>Less uncertainty after zero observed loss</h2><p>After 40 zero-loss decisions, the residual mean upper bound is <strong>${money(zero.v2_upper_usd)}</strong>, compared with <strong>${money(zero.v1_upper_usd)}</strong> for the earlier Hoeffding method at the same error budget.</p><p>Both proposed and residual streams receive 2.5% error, giving 95% family coverage under fixed conditional tail probabilities.</p><h2>Explicit tradeoffs</h2><p>The mixture improves moderate-rate detection and later-shift response. Strong signals can take more observations to trigger than the original aggressive bet. Bayesian credible intervals remain prior-sensitive.</p><a href="https://github.com/farzana0/riskgraph/blob/main/docs/FRAMEWORK_V2.md" target="_blank" rel="noreferrer">Read the full comparison ↗</a></article></div><p class="benchmark-note">Synthetic evaluations establish behavior under the recorded generators. They do not establish a production error rate, a causal Claude memory benefit, or resistance to arbitrary attacks. All numerical comparisons are from seed ${data.seed}.</p>`;
    benchmarksLoaded=true;
  }catch(error){$("benchmark-content").textContent="Validation results could not be loaded. "+error.message;}
}
async function refreshConfig(){
  config=await api("/api/config");accessState();
  $("anthropic-status").textContent=config.anthropic_configured?`Configured · ${config.model}. ${config.claude_attempts_used} / ${config.claude_attempts_limit} attempts used.`:"Not configured · offline evaluations available.";
  $("surreal-status").textContent=config.surreal_configured?"Configured · hosted incident storage and retrieval. Per-decision provenance records the actual result.":"Not configured · local demonstration memory available.";
  $("mode").options[1].disabled=!config.live_enabled;updateRunSettings();
}
async function loadStress(){
  try{
    const response=await api('/api/stress');if(!response.available)return;
    const data=response.study,summary=data.summary;
    const groups={identity:"Identity & ownership",manipulation:"Instructions & false authority",payment_edges:"Amounts & payment history",compound:"Combined failures & boundaries"};
    const library=Object.entries(groups).map(([group,label])=>`<article><h3>${escapeText(label)}</h3><ul>${Object.values(data.catalogue).filter(row=>row.group===group).map(row=>`<li>${escapeText(row.label)}</li>`).join('')}</ul></article>`).join('');
    $('stress-content').innerHTML=`<article class="panel campaign-results"><div class="panel-heading"><div><div class="eyebrow">EXPANDED FAILURE CAMPAIGN</div><h2>${summary.failure_scenarios} distinct scenarios. One independent gate.</h2><p>Scripted faults test the controls even when the agent makes a mistake.</p></div></div><div class="benchmark-metrics"><article><strong>${integer(summary.policy_proposals)}</strong><p>Policy proposals tested<br>${integer(summary.harmful_proposals)} could cause loss</p></article><article><strong>${summary.harmful_allowed}</strong><p>Harmful proposals allowed<br>Within this synthetic campaign</p></article><article><strong>${integer(summary.workflow_decisions)}</strong><p>End-to-end decisions<br>${summary.adapter_faults} provider faults also tested</p></article></div><p class="benchmark-note">${integer(summary.authorized_proposals)} reference-authorized proposals were tested; ${summary.authorized_blocked} were wrongly blocked. Six memory conditions and ${summary.integrity_checks} replay or tampering checks are recorded separately. These injected faults do not estimate how often Claude fails in production.</p></article><details class="panel scenario-library" open><summary>Explore the 28 failure scenarios</summary><div class="scenario-library-grid">${library}</div></details><details class="panel scenario-library"><summary>Provider failures & operational controls</summary><div class="scenario-library-grid"><article><h3>Provider faults · no payment executed</h3><ul>${data.adapter_failures.map(row=>`<li>${escapeText(title(row.failure))}</li>`).join('')}</ul></article><article><h3>Memory & record integrity</h3><ul>${data.memory_failures.map(row=>`<li>${escapeText(title(row.fault))}</li>`).join('')}${data.integrity_failures.filter((row,i,all)=>all.findIndex(r=>r.failure===row.failure)===i).map(row=>`<li>${escapeText(title(row.failure))}</li>`).join('')}</ul><p class="form-help">External source-data authenticity, live payment infrastructure, and aggregate limits across orders remain outside the implemented model.</p></article></div></details>`;
  }catch(error){$('stress-content').textContent='Expanded stress results could not be loaded. '+error.message;}
}
async function init(){
  await refreshConfig();
  const runs=await history();if(runs.length){
    const featured=runs.find(run=>run.mode==="offline"&&run.suite==="full_stress"&&run.prompt_version==="injected-failures-v2"&&run.status==="complete"&&run.count>=28)||runs[0];
    snapshot=await api(`/api/runs/${featured.id}`);$("run-select").value=featured.id;render();
  }else{$("run-label").textContent="No evaluations yet";$("assessment-title").textContent="Ready to evaluate";$("assessment-description").textContent="Choose New evaluation to collect synthetic decision evidence.";}
}
init().catch(error=>notice(`Could not load dashboard: ${error.message}`));
