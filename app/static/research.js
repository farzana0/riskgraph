'use strict';
(() => {
  const $ = id => document.getElementById(id), NS='http://www.w3.org/2000/svg';
  const labels={agent:'Agent only',critic:'Critic',memory:'Memory',both:'Memory + critic'};
  const state={study:null,model:'claude-haiku-5-5',setup:'agent',index:0,view:'workflow',returnFocus:null};
  const title=s=>s.replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
  const pct=x=>x==null?'Unavailable':(x*100).toFixed(1)+'%';
  const pp=x=>x==null?'Unavailable':(x>0?'+':'')+(x*100).toFixed(1)+' pp';
  const usd=x=>x==null?'Unavailable':x.toLocaleString('en-US',{style:'currency',currency:'USD'});
  const modelName=x=>x.includes('haiku')?'Haiku':'Sonnet';
  const range=(a,format=pct)=>a?format(a[0])+' to '+format(a[1]):'Unavailable';
  const clear=n=>n.replaceChildren();
  function el(tag,attrs={},parent){const n=document.createElement(tag);for(const [k,v] of Object.entries(attrs)){if(k==='text')n.textContent=v;else n.setAttribute(k,v);}if(parent)parent.append(n);return n;}
  function svg(tag,attrs={},parent){const n=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs)){if(k==='text')n.textContent=v;else n.setAttribute(k,v);}if(parent)parent.append(n);return n;}
  const selected=()=>state.study.cells.find(c=>c.case_id===state.study.cases[state.index].id&&c.model===state.model&&c.memory===['memory','both'].includes(state.setup));
  const arm=()=>state.study.analysis.arms[state.model+':'+state.setup];
  function showDetails(name,parts){
    state.returnFocus=document.activeElement;$('research-dialog-title').textContent=name;const b=$('research-dialog-body');clear(b);
    for(const [heading,content] of parts){el('h3',{text:heading},b);if(typeof content==='string')el('p',{text:content},b);else el('pre',{text:JSON.stringify(content,null,2)},b);}
    $('research-dialog').showModal();$('research-dialog-close').focus();
  }
  function table(host,headers,rows){const wrap=el('div',{class:'table-scroll'},host),t=el('table',{},wrap),h=el('tr',{},el('thead',{},t));headers.forEach(text=>el('th',{text,scope:'col'},h));const body=el('tbody',{},t);rows.forEach(row=>{const tr=el('tr',{},body);row.forEach((text,i)=>el(i?'td':'th',{text,...(i?{}:{scope:'row'})},tr));});}
  function node(host,key,x,y,name,detail,glyph,kind,tone,callback){
    const g=svg('g',{class:'study-node '+(tone||''),transform:`translate(${x} ${y})`,role:'button',tabindex:0,'aria-label':name+'. '+detail+'. Inspect saved evidence.'},host);
    svg('rect',{class:'node-hit',x:-76,y:-26,width:152,height:90},g);
    if(kind==='input')svg('path',{class:'shape',d:'M0 -17 L17 0 L0 17 L-17 0 Z'},g);
    else if(kind==='agent')svg('circle',{r:20},g);else svg('rect',{x:-18,y:-18,width:36,height:36,rx:kind==='memory'?10:4},g);
    svg('text',{y:4,'text-anchor':'middle',text:glyph},g);svg('text',{class:'node-name',y:39,'text-anchor':'middle',text:name},g);svg('text',{class:'node-detail',y:56,'text-anchor':'middle',text:detail},g);
    g.addEventListener('click',callback);g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();callback();}});return g;
  }
  function edge(host,a,b,label,disabled=false,data=false){
    const d=`M${a[0]} ${a[1]} L${b[0]} ${b[1]}`;svg('path',{class:'study-edge'+(disabled?' disabled':'')+(data?' data':''),d},host);
    if(label)svg('text',{class:'edge-label',x:(a[0]+b[0])/2+7,y:(a[1]+b[1])/2-8,text:label},host);
  }
  function renderWorkflow(){
    const s=state.study,c=s.cases[state.index],cell=selected(),critic=['critic','both'].includes(state.setup),memory=['memory','both'].includes(state.setup);
    $('research-title').textContent=title(c.family)+' · request '+(state.index+1);
    $('research-caption').textContent=modelName(state.model)+' · '+labels[state.setup]+' · saved calls, illustrative layout; no new call on selection.';
    const stage=critic?'corrected':'initial',call=cell?.[stage],out=cell?.[stage+'_outcome'];
    $('research-outcome').textContent=!out?'Not processed':!out.resolved?'Unresolved response':out.proposed_loss_cents>0?'Unsafe proposal · '+usd(out.proposed_loss_cents/100):out.task_failure?'Service / task error':'Task correct';
    const g=$('research-graph');clear(g);const phone=innerWidth<=750;g.setAttribute('viewBox',phone?'0 0 370 650':'0 0 1000 365');
    const p=phone?{input:[65,65],records:[290,65],memory:[65,190],actor:[245,190],critic:[245,330],gate:[245,465],payment:[65,465],score:[65,590]}:{input:[75,175],records:[75,65],memory:[285,55],actor:[285,175],critic:[495,175],gate:[680,175],payment:[875,90],score:[875,275]};
    const initial=cell?.initial,final=call;
    edge(g,p.input,p.actor,'request');edge(g,p.records,p.actor,phone?'':'authenticated records',false,true);edge(g,p.memory,p.actor,memory?'source hits':'memory off',!memory,true);
    edge(g,p.actor,p.critic,critic?'proposal':phone?'':'critic off',!critic);
    if(critic)edge(g,p.critic,p.gate,'revision');
    else{svg('path',{class:'study-edge',d:phone?'M245 210 C365 220 365 445 245 445':'M305 175 C380 105 600 105 660 175'},g);svg('text',{class:'edge-label',x:phone?295:440,y:phone?390:112,text:'initial proposal'},g);}
    const allowed=!!out?.resolved&&out.gate.allowed&&final?.proposal?.action==='refund';
    edge(g,p.gate,p.payment,allowed?usd(out.executed_cents/100):'not paid',!allowed);edge(g,allowed?p.payment:p.gate,p.score,'score');
    const memoryFact=s.memory?.families[c.family];
    node(g,'input',...p.input,'Request',usd(c.truth.requested_cents/100)+' requested','?', 'input','',()=>showDetails('Customer request',[['Supplied request',c.observation.authenticated_request],['Untrusted note',c.observation.untrusted_customer_note||c.observation.untrusted_customer_message]]));
    node(g,'records',...p.records,'Connector records','Authenticated source','≡','input','',()=>showDetails('Records supplied to the model',[['Connector records',c.observation.authenticated_connector_records],['Scoring boundary','The canonical scoring state is withheld from all model calls.']]));
    node(g,'memory',...p.memory,'SurrealDB memory',memory?(memoryFact?.hits.length||0)+' frozen source hits':'Disabled','≋','memory',memory?'':'disabled',()=>showDetails('SurrealDB retrieval',[['Intervention',memory?'This request received the frozen retrieved sources below.':'Memory is off for this cell. These sources were not supplied to this model request.'],['Retrieved procedural guidance',memory?memoryFact?.prior_text||'Unavailable':'Not supplied'],['Frozen source evidence',memory?memoryFact:{status:'disabled'}],['Interpretation',s.analysis.memory_interpretation]]));
    const describe=r=>r?.status==='complete'?title(r.proposal.action)+' '+usd(r.proposal.amount_cents/100):r?.status||'Not processed';
    node(g,'actor',...p.actor,modelName(state.model)+' agent',describe(initial),'●','agent',cell?.initial_outcome?.proposed_loss_cents>0?'bad':'',()=>showDetails('Initial proposal',[['Recorded response',initial||{status:'not_processed'}],['Independently scored outcome',cell?.initial_outcome||{status:'not_processed'}]]));
    node(g,'critic',...p.critic,'Sonnet critic',critic?describe(call):'Disabled','●','agent',critic?(out?.proposed_loss_cents>0?'bad':''):'disabled',()=>showDetails('Corrective critic',[['Role','A separate Sonnet call may revise the original proposal. It cannot authorize payment.'],['Recorded response',critic?cell?.corrected||{status:'not_processed'}:{status:'disabled'}],['Scored revision',critic?out||{status:'not_processed'}:{status:'disabled'}]]));
    node(g,'gate',...p.gate,'Policy gate',out?.resolved?(out.gate.allowed?'Passes policy':'Stops proposal'):'No valid proposal','§','tool',out?.resolved&&!out.gate.allowed?'bad':'',()=>showDetails('Independent policy gate',[['Checks',out?.gate||{status:'unresolved'}],['Canonical scoring state (not given to models)',c.truth]]));
    node(g,'payment',...p.payment,'Simulated payment',out?.resolved?usd(out.executed_cents/100)+' executed':'Unavailable','$','tool','',()=>showDetails('Simulated ledger outcome',[['Settlement',out||{status:'not_processed'}],['Scope','Only synthetic balances change. No external payment service is called.']]));
    node(g,'score',...p.score,'Evaluator',out?.resolved?usd(out.proposed_loss_cents/100)+' proposed harm':'Unavailable','Δ','tool',out?.proposed_loss_cents>0?'bad':'ok',()=>showDetails('Independent scoring',[['Financial and task outcome',out||{status:'not_processed'}],['Expected refund',usd(c.expected_refund_cents/100)+' under the benchmark policy. Zero may indicate decline or required escalation.']]));
    const cards=$('research-cards');clear(cards);
    for(const [setup,label] of Object.entries(labels)){
      const cc=s.cells.find(x=>x.case_id===c.id&&x.model===state.model&&x.memory===['memory','both'].includes(setup));const r=cc?.[['critic','both'].includes(setup)?'corrected_outcome':'initial_outcome'];
      const b=el('button',{'aria-pressed':String(setup===state.setup)},cards);el('strong',{text:label},b);el('span',{text:!r?'Not processed':!r.resolved?'Financial outcome unresolved':usd(r.proposed_loss_cents/100)+' proposed harm'},b);el('small',{text:r?(r.task_failure?'Task error':'Task correct'):'Pending'},b);b.onclick=()=>{$('research-setup').value=setup;state.setup=setup;render();};
    }
    $('research-case-note').textContent='This is one example. Aggregate comparisons include every scheduled case and retain corrections, regressions and unresolved responses. The independent gate is present in all four setups.';
  }
  function renderRisk(){
    const a=arm();if(!a)return;
    $('research-arm-name').textContent=modelName(state.model)+' · '+labels[state.setup];
    const metrics=$('research-metrics');clear(metrics);
    const metric=(label,value,note)=>{const d=el('div',{class:'study-metric'},metrics);el('span',{class:'metric-label',text:label},d);el('strong',{text:value},d);el('small',{text:note},d);};
    metric('Harmful proposal probability',pct(a.frequency_mean),'95% Bayesian credible: '+range(a.frequency_credible95));
    metric('Observed harmful proposals',a.harmful+' / '+a.resolved,a.unresolved+' unresolved · '+a.task_errors+' task errors');
    metric('Observed proposed loss',usd(a.observed_mean_usd)+' / case',usd(a.observed_loss_usd)+' total exact-dollar proposed loss');
    metric('Binned loss posterior',usd(a.binned_loss_mean_usd)+' / case','95% credible: '+range(a.binned_loss_credible95,usd)+'; severity prior and upward bins matter.');
    metric('Observed loss after gate',usd(a.residual_loss_usd),'Conditional mean upper: '+usd(a.residual_conditional_bound.upper_usd)+' / completed case. Zero observations retain uncertainty.');
    const g=$('research-risk-graph');clear(g);const phone=innerWidth<=750;g.setAttribute('viewBox',phone?'0 0 370 350':'0 0 760 250');
    const boxes=phone?[[12,20,160,70],[198,20,160,70],[12,135,160,70],[198,135,160,70],[85,265,200,70]]:[[10,20,175,75],[235,20,175,75],[10,145,175,75],[235,145,175,75],[490,85,250,90]];
    const content=[['Observed outcomes',a.resolved+' completed',a.harmful+' harmful · '+a.unresolved+' unresolved'],['Family posteriors',pct(a.frequency_mean),'12 × Beta(.5+k, .5+n−k)'],['Severity + prior','Four loss bands','$25 / 100 / 500 / 1000'],['Assumed mix','1/12 per family','Fixed challenge weights'],['Weighted binned risk',usd(a.binned_loss_mean_usd)+' / case','Σ weight × probability × severity']];
    const connections=phone?[[[172,55],[198,55]],[[92,90],[92,135]],[[92,205],[150,265]],[[278,205],[245,265]]]:[[[185,57],[235,57]],[[97,95],[97,145]],[[410,57],[490,115]],[[185,182],[490,140]],[[410,182],[490,150]]];
    if(phone)svg('path',{class:'study-edge',d:'M278 90 C370 110 370 230 255 265'},g);
    connections.forEach(([p,q])=>edge(g,p,q,''));
    boxes.forEach(([x,y,w,h],i)=>{svg('rect',{class:'risk-model-box',x,y,width:w,height:h,rx:8},g);svg('text',{class:'risk-model-label',x:x+12,y:y+19,text:content[i][0]},g);svg('text',{class:'risk-model-value',x:x+12,y:y+41,text:content[i][1]},g);svg('text',{class:'risk-model-small',x:x+12,y:y+58,text:content[i][2]},g);});
    const rows=state.study.analysis.comparisons.filter(c=>c.kind!=='model'&&c.before.startsWith(state.model+':'));
    const effects=$('research-effects');clear(effects);effects.setAttribute('viewBox',phone?'0 0 370 320':'0 0 680 250');svg('title',{text:rows.map(r=>effectLabel(r)+': '+pp(r.posterior_frequency_reduction)+'; 95% credible '+range(r.credible95,pp)).join('. ')},effects);
    const X=p=>phone?140+(p+1)*105:260+(p+1)*195;
    svg('line',{class:'effect-zero',x1:X(0),x2:X(0),y1:20,y2:phone?275:205},effects);
    [-1,-.5,0,.5,1].forEach(p=>svg('text',{class:'effect-text',x:X(p),y:phone?305:235,'text-anchor':'middle',text:(100*p)+' pp'},effects));
    rows.forEach((r,i)=>{const y=phone?42+i*65:38+i*48;svg('text',{class:'effect-text',x:5,y:phone?y-19:y+4,text:effectLabel(r)},effects);svg('line',{class:'effect-line',x1:X(r.credible95[0]),x2:X(r.credible95[1]),y1:y,y2:y},effects);svg('circle',{class:'effect-dot',cx:X(r.posterior_frequency_reduction),cy:y,r:4},effects);});
    const details=$('research-effect-detail');clear(details);
    rows.forEach(r=>{const d=el('div',{class:'effect-case'},details);el('strong',{text:effectLabel(r)+' · observed '+pp(r.observed_frequency_reduction)+' reduction'},d);el('div',{text:r.avoided+' harmful proposals avoided · '+r.introduced+' introduced · '+r.resolved_pairs+'/'+r.scheduled_pairs+' matched pairs'},d);el('small',{text:'Posterior reduction '+pp(r.posterior_frequency_reduction)+' [95% credible '+range(r.credible95,pp)+']. '+(r.credible95[0]<=0&&r.credible95[1]>=0?'Interval crosses zero.':'Conditional on stated priors and workload.')},d);el('small',{text:'Task errors fixed / introduced: '+r.task_errors_fixed+' / '+r.task_errors_introduced+'. Observed proposed-loss reduction: '+usd(r.observed_loss_reduction_usd)+' / matched case.'},d);});
    clear($('research-scenarios'));table($('research-scenarios'),['Family','Harm / resolved','Frequency mean','95% credible'],Object.entries(a.cells).map(([f,c])=>[title(f),c.k+' / '+c.n,pct(c.posterior_mean),range(c.credible95)]));
  }
  function effectLabel(r){const setup=r.before.split(':')[1];return r.kind==='critic'?'Critic · memory '+(setup==='memory'?'on':'off'):'Memory · critic '+(setup==='critic'?'on':'off');}
  function render(){if(!state.study?.analysis)return;renderWorkflow();renderRisk();}
  function changeView(view){state.view=view;for(const name of ['workflow','risk']){const active=name===view;$('research-'+name).hidden=!active;$('research-'+name+'-tab').setAttribute('aria-selected',String(active));$('research-'+name+'-tab').tabIndex=active?0:-1;}render();}
  function example(kind){
    if(!state.study)return;
    const changed=(a,b)=>a&&b&&(a.resolved!==b.resolved||a.task_failure!==b.task_failure||a.proposed_loss_cents!==b.proposed_loss_cents);
    const candidates=state.study.cells.filter(c=>c.model===state.model).filter(c=>kind==='critic'?changed(c.initial_outcome,c.corrected_outcome):!c.memory&&changed(c.initial_outcome,state.study.cells.find(m=>m.case_id===c.case_id&&m.model===c.model&&m.memory)?.initial_outcome));
    if(!candidates.length){showDetails('No observed '+kind+' change',[['Selected model','No change in task-error status, resolution or proposed unauthorized loss is recorded for this model in the processed cases. This is not proof of equivalence.']]);return;}
    const next=candidates.find(c=>state.study.cases.findIndex(x=>x.id===c.case_id)>state.index)||candidates[0];state.index=state.study.cases.findIndex(c=>c.id===next.case_id);state.setup=kind==='memory'?'memory':next.memory?'both':'critic';$('research-case').value=state.index;$('research-setup').value=state.setup;render();
  }
  async function load(){
    $('research-refresh').disabled=true;
    try{const r=await fetch('/api/research-study');if(!r.ok)throw Error('HTTP '+r.status);const data=await r.json();if(!data.available){$('research-status').textContent='The new experiment is preparing its frozen SurrealDB memory bank. No result is available yet. Refresh to check progress.';return;}
      const s=data.study;if(!s.analysis){$('research-status').textContent='Experiment '+s.status+'; waiting for the first completed matched case.';return;}state.study=s;
      const ids=$('research-case');clear(ids);s.cases.forEach((c,i)=>el('option',{value:i,text:String(i+1).padStart(2,'0')+' · '+title(c.family)},ids));ids.value=state.index;
      ['research-model','research-case','research-setup'].forEach(id=>$(id).disabled=false);
      const processed=new Set(s.cells.map(c=>c.case_id)).size;$('research-status').classList.remove('error');$('research-status').textContent=s.status+' · '+processed+'/'+s.cases.length+' cases · '+s.budget.requests_reserved+' real model requests · '+usd(s.budget.accounted_estimated_usd)+' estimated token cost · frozen SurrealDB sources for '+Object.keys(s.memory.families).length+' families.';
      render();
    }catch(e){$('research-status').classList.add('error');$('research-status').textContent='Could not refresh results: '+e.message+(state.study?'. Earlier recorded results remain displayed.':'');}finally{$('research-refresh').disabled=false;}
  }
  $('research-model').onchange=e=>{state.model=e.target.value;render();};$('research-case').onchange=e=>{state.index=Number(e.target.value);render();};$('research-setup').onchange=e=>{state.setup=e.target.value;render();};$('research-refresh').onclick=load;
  $('research-memory-example').onclick=()=>example('memory');$('research-critic-example').onclick=()=>example('critic');
  for(const view of ['workflow','risk']){$('research-'+view+'-tab').onclick=()=>changeView(view);$('research-'+view+'-tab').onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const next=e.key==='Home'?'workflow':e.key==='End'?'risk':view==='workflow'?'risk':'workflow';changeView(next);$('research-'+next+'-tab').focus();}};}
  $('research-dialog-close').onclick=()=>$('research-dialog').close();$('research-dialog').onclose=()=>{if(state.returnFocus?.isConnected)state.returnFocus.focus();};
  $('research-methods').onclick=()=>showDetails('Study design and interpretation',state.study?[['Design',state.study.design.scope],['Memory',state.study.analysis.memory_interpretation],['Prior',state.study.analysis.prior],['Uncertainty',state.study.analysis.uncertainty],['Reproducibility',state.study.design],['Protocol','Full protocol and raw report: /api/research-study and GitHub docs/REAL_MEMORY_STUDY.md. No new calls run when browsing these graphs.']]:[['Status','The registered experiment is preparing. Refresh to check for recorded results.']]);
  $('research-bounds').onclick=()=>{const a=arm();showDetails('Conservative bounds and missing outcomes',[['Frequency exact upper endpoint',pct(a.exact_upper)+'; fixed-batch simultaneous upper bounds over 96 family/configuration cells.'],['Conditional proposed-loss interval',range([a.conditional_loss_bound.lower_usd,a.conditional_loss_bound.upper_usd],usd)+' / completed case.'],['Unresolved sensitivity',a.missing_outcome_mean_range_usd?range(a.missing_outcome_mean_range_usd,usd)+' per processed case, assigning each unknown proposed loss anywhere in $0–$1,000. This is a sensitivity range, not a confidence interval.':'Unavailable'],['Matched comparisons',state.study.analysis.comparisons.filter(c=>c.before.startsWith(state.model+':'))],['Assumptions and separate error budgets',state.study.analysis.uncertainty]]);};
  $('research-all-arms').onclick=()=>{showDetails('Haiku and Sonnet · every configuration',[['Interpretation','Same 48 scheduled cases. Interventions add context or compute. Model differences are not a claim of universal superiority. Zero after-gate loss is distinct from unsafe proposals.']]);const host=$('research-dialog-body');table(host,['Model / setup','Harm / resolved','Task errors','Posterior frequency [95% credible]','Observed proposed loss'],Object.values(state.study.analysis.arms).map(a=>[modelName(a.model)+' · '+labels[a.setup],a.harmful+' / '+a.resolved,a.task_errors,pct(a.frequency_mean)+' ['+range(a.frequency_credible95)+']',usd(a.observed_loss_usd)]));el('h3',{text:'Matched model differences'},host);el('p',{text:'Positive reduction favors Sonnet relative to Haiku on the same cases. Use the paired contrast intervals below rather than comparing separate arm intervals. Intervals crossing zero are inconclusive.'},host);table(host,['Setup','Matched pairs','Avoided / introduced','Observed reduction','Joint posterior reduction [95% credible]'],state.study.analysis.comparisons.filter(c=>c.kind==='model').map(c=>[labels[c.before.split(':')[1]],c.resolved_pairs+' / '+c.scheduled_pairs,c.avoided+' / '+c.introduced,pp(c.observed_frequency_reduction),pp(c.posterior_frequency_reduction)+' ['+range(c.credible95,pp)+']']));};
  addEventListener('resize',render);load();
})();
