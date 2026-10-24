'use strict';
(() => {
  const $ = id => document.getElementById(id), NS='http://www.w3.org/2000/svg';
  const labels={none:'No memory',raw:'Raw memory',selected:'Selected memory',grounded:'Memory + calculations'};
  const state={study:null,model:'claude-haiku-5-5',setup:'grounded',critic:false,index:0,view:'workflow',returnFocus:null};
  const title=s=>s.replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
  const pct=x=>x==null?'Unavailable':(x*100).toFixed(1)+'%';
  const pp=x=>x==null?'Unavailable':(x>0?'+':'')+(x*100).toFixed(1)+' pp';
  const usd=x=>x==null?'Unavailable':x.toLocaleString('en-US',{style:'currency',currency:'USD'});
  const modelName=x=>x.includes('haiku')?'Haiku':'Sonnet';
  const range=(a,format=pct)=>a?format(a[0])+' to '+format(a[1]):'Unavailable';
  const clear=n=>n.replaceChildren();
  function el(tag,attrs={},parent){const n=document.createElement(tag);for(const [k,v] of Object.entries(attrs)){if(k==='text')n.textContent=v;else n.setAttribute(k,v);}if(parent)parent.append(n);return n;}
  function svg(tag,attrs={},parent){const n=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs)){if(k==='text')n.textContent=v;else n.setAttribute(k,v);}if(parent)parent.append(n);return n;}
  const selected=()=>state.study.cells.find(c=>c.case_id===state.study.cases[state.index].id&&c.model===state.model&&c.memory_mode===state.setup);
  const arm=()=>state.study.analysis.arms[state.model+'|'+state.setup+'|'+Number(state.critic)];
  function showDetails(name,parts){
    state.returnFocus=document.activeElement;$('research-dialog-title').textContent=name;const b=$('research-dialog-body');clear(b);
    for(const [heading,content] of parts){el('h3',{text:heading},b);if(typeof content==='string')el('p',{text:content},b);else el('pre',{text:JSON.stringify(content,null,2)},b);}
    $('research-dialog').showModal();$('research-dialog-close').focus();
  }
  function table(host,headers,rows){const wrap=el('div',{class:'table-scroll'},host),t=el('table',{},wrap),h=el('tr',{},el('thead',{},t));headers.forEach(text=>el('th',{text,scope:'col'},h));const body=el('tbody',{},t);rows.forEach(row=>{const tr=el('tr',{},body);row.forEach((text,i)=>el(i?'td':'th',{text,...(i?{}:{scope:'row'})},tr));});}
  function node(host,key,x,y,name,detail,glyph,kind,tone,callback){
    const g=svg('g',{class:'study-node '+(tone||''),transform:`translate(${x} ${y})`,role:'button',tabindex:0,'data-node':key,'aria-label':name+'. '+detail+'. Inspect saved evidence.'},host);
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
  function rowFor(mode){return state.study.cells.find(c=>c.case_id===state.study.cases[state.index].id&&c.model===state.model&&c.memory_mode===mode);}
  const outcomeFor=c=>c?.[state.critic?'corrected_outcome':'initial_outcome'];
  const callFor=c=>c?.[state.critic?'corrected':'initial'];
  function renderWorkflow(){
    const s=state.study,c=s.cases[state.index],cell=selected(),out=outcomeFor(cell),current=callFor(cell),memory=state.setup!=='none',guided=['selected','grounded'].includes(state.setup),grounded=state.setup==='grounded',prep=s.prepared[c.id];
    $('research-title').textContent=title(c.family)+' · request '+(state.index+1);
    $('research-caption').textContent=modelName(state.model)+' · '+labels[state.setup]+' · critic '+(state.critic?'on':'off')+'. Recorded calls; calculations are a separate deterministic preflight.';
    $('research-outcome').textContent=!out?'Not processed':!out.resolved?'Unresolved response':out.proposed_loss_cents>0?'Unsafe proposal · '+usd(out.proposed_loss_cents/100):out.task_failure?'Service / task error':'Task correct';
    const g=$('research-graph');clear(g);const phone=innerWidth<=750;g.setAttribute('viewBox',phone?'0 0 370 840':'0 0 1180 420');
    const p=phone?{input:[65,55],records:[290,55],memory:[65,205],calcs:[65,385],actor:[265,230],critic:[265,420],gate:[265,610],payment:[65,610],score:[65,770]}:{input:[75,185],records:[75,65],memory:[340,55],calcs:[340,335],actor:[340,185],critic:[610,185],gate:[830,185],payment:[1050,90],score:[1050,315]};
    edge(g,p.input,p.actor,'request');edge(g,p.records,p.actor,'',false,true);
    if(guided)edge(g,p.records,p.memory,'',false,true);
    edge(g,p.memory,p.actor,'',!memory,true);
    if(memory&&state.critic)svg('path',{class:'study-edge data',d:phone?'M83 205 C150 225 120 420 245 420':'M358 55 C600 15 670 60 610 165'},g);
    if(grounded){
      svg('path',{class:'study-edge data',d:phone?'M290 75 C365 140 175 360 83 385':'M93 65 C160 150 145 335 322 335'},g);
      svg('path',{class:'study-edge data',d:phone?'M83 385 C170 385 190 285 245 250':'M358 335 C470 315 455 230 360 205'},g);
      if(state.critic)svg('path',{class:'study-edge data',d:phone?'M83 385 L245 420':'M358 335 C600 335 650 270 610 205'},g);
    }
    edge(g,p.actor,p.critic,state.critic?'proposal':'',!state.critic);
    if(state.critic)edge(g,p.critic,p.gate,'revision');
    else svg('path',{class:'study-edge',d:phone?'M285 230 C365 260 365 590 285 610':'M360 185 C500 105 690 105 810 185'},g);
    const paid=!!out?.resolved&&out.gate.allowed&&current?.proposal?.action==='refund';edge(g,p.gate,p.payment,'',!paid);edge(g,paid?p.payment:p.gate,p.score,'score');
    const showCall=(name,call,result)=>showDetails(name,[['Recorded response',call||{status:'not_processed'}],['Independently scored outcome',result||{status:'not_processed'}]]);
    node(g,'input',...p.input,'Request',usd(c.truth.requested_cents/100)+' requested','?','input','',()=>showDetails('Customer request',[['Authenticated request',c.observation.authenticated_request],['Untrusted note',c.observation.untrusted_customer_note]]));
    node(g,'records',...p.records,'Connector records','Current evidence','≡','input','',()=>showDetails('Current records',[['Supplied records',c.observation.authenticated_connector_records],['Boundary','No scoring truth, expected refund or held-out answer is supplied to an agent or the preflight calculator.']]));
    const detail=!memory?'Disabled':guided?prep.plan.length+' verified skill'+(prep.plan.length===1?'':'s'):s.memory.raw[c.family].hits.length+' raw source hits';
    node(g,'memory',...p.memory,'SurrealDB recall',detail,'≋','memory',memory?'':'disabled',()=>{
      if(!memory){showDetails('SurrealDB recall',[['Status','No memory context is supplied in this strategy.']]);return;}
      const records=guided?Object.fromEntries(prep.plan.map(skill=>[skill,s.memory.skills[skill]])):s.memory.raw[c.family];
      showDetails('SurrealDB recall',[['Strategy',guided?'Current connector capabilities select at most three version/content/validity-checked skills. The compact selected context is shared with the critic when enabled.':'Legacy control: one raw family hint from the actual earlier SurrealDB bank.'],['Capability plan',guided?prep.plan:{control_family:c.family}],['Context supplied to models',guided?prep.selected_context:s.memory.raw[c.family].hits],['Retrieval traces and source evidence',records],['Interpretation',s.analysis.memory_interpretation]]);
    });
    node(g,'calcs',...p.calcs,'Record calculations',grounded?prep.calculations.status:'Disabled','∑','tool',grounded?'':'disabled',()=>showDetails('Record calculations',[['Role','Deterministic preflight, run by the orchestrator from visible current records. It is not an LLM-invoked tool or a scoring oracle. Only the Memory + calculations strategy receives this report.'],['Report supplied to model',grounded?prep.calculations:{status:'disabled'}]]));
    const describe=call=>call?.status==='complete'?title(call.proposal.action)+' '+usd(call.proposal.amount_cents/100):({invalid_response:'Incomplete response',provider_error:'Provider unavailable',not_started:'Not started'}[call?.status]||'Not processed');
    node(g,'actor',...p.actor,modelName(state.model)+' agent',describe(cell?.initial),'●','agent',cell?.initial_outcome?.proposed_loss_cents>0?'bad':'',()=>showCall('Initial proposal',cell?.initial,cell?.initial_outcome));
    node(g,'critic',...p.critic,'Sonnet critic',state.critic?describe(cell?.corrected):'Disabled','●','agent',state.critic?(out?.proposed_loss_cents>0?'bad':''):'disabled',()=>showCall('Corrective critic',state.critic?cell?.corrected:{status:'disabled'},state.critic?out:{status:'disabled'}));
    node(g,'gate',...p.gate,'Policy gate',out?.resolved?(out.gate.allowed?'Passes policy':'Stops proposal'):'No valid proposal','§','tool',out?.resolved&&!out.gate.allowed?'warn':'',()=>showDetails('Independent policy gate',[['Checks',out?.gate||{status:'unresolved'}],['Scoring state withheld from the agents',c.truth]]));
    node(g,'payment',...p.payment,'Simulated payment',out?.resolved?usd(out.executed_cents/100)+' executed':'Unavailable','$','tool','',()=>showDetails('Synthetic settlement',[['Outcome',out||{status:'not_processed'}],['Scope','No external payment service is called.']]));
    node(g,'score',...p.score,'Evaluator',out?.resolved?usd(out.proposed_loss_cents/100)+' proposed harm':'Unavailable','Δ','tool',out?.resolved?(out.proposed_loss_cents>0?'bad':'ok'):'',()=>showDetails('Scored outcome',[['Financial and task outcome',out||{status:'not_processed'}],['Expected refund under the benchmark',usd(c.expected_refund_cents/100)]]));
    const cards=$('research-cards');clear(cards);
    for(const [mode,label] of Object.entries(labels)){
      const r=outcomeFor(rowFor(mode)),b=el('button',{'aria-pressed':String(mode===state.setup)},cards);el('strong',{text:label},b);el('span',{text:!r?'Not processed':!r.resolved?'Financial outcome unresolved':usd(r.proposed_loss_cents/100)+' proposed harm'},b);el('small',{text:!r?'Pending':r.task_failure?'Task error':'Task correct'},b);b.onclick=()=>{state.setup=mode;$('research-setup').value=mode;render();};
    }
    $('research-case-note').textContent='One recorded example; aggregate estimates retain all 36 scheduled cases. Cards hold the model and critic setting fixed. Raw → selected changes retrieval and use; selected → calculations adds arithmetic support. The fixed gate is present in every strategy.';
  }
  function renderRisk(){
    const a=arm();if(!a)return;
    $('research-arm-name').textContent=modelName(state.model)+' · '+labels[state.setup]+' · critic '+(state.critic?'on':'off');
    const metrics=$('research-metrics');clear(metrics);
    const metric=(label,value,note)=>{const d=el('div',{class:'study-metric'},metrics);el('span',{class:'metric-label',text:label},d);el('strong',{text:value},d);el('small',{text:note},d);};
    metric('Posterior harm probability',pct(a.frequency_mean),'95% Bayesian credible: '+range(a.frequency_credible95));
    metric('Observed harmful proposals',a.harmful+' / '+a.resolved,a.unresolved+' unresolved · '+a.task_errors+' task errors');
    metric('Observed proposed loss',usd(a.observed_mean_usd)+' / case',usd(a.observed_loss_usd)+' total proposed loss; mean uses '+a.resolved+' completed cases');
    metric('Binned loss posterior',usd(a.binned_loss_mean_usd)+' / case','95% credible: '+range(a.binned_loss_credible95,usd)+'; prior-sensitive modelled loss, not observed loss.');
    metric('Observed loss after gate',usd(a.residual_loss_usd),'Conditional mean upper: '+usd(a.residual_conditional_bound.upper_usd)+' / completed case. Zero observations retain uncertainty.');
    const g=$('research-risk-graph');clear(g);const phone=innerWidth<=750;g.setAttribute('viewBox',phone?'0 0 370 350':'0 0 760 250');
    const boxes=phone?[[12,20,160,70],[198,20,160,70],[12,135,160,70],[198,135,160,70],[85,265,200,70]]:[[10,20,175,75],[235,20,175,75],[10,145,175,75],[235,145,175,75],[490,85,250,90]];
    const content=[['Observed outcomes',a.resolved+' completed',a.harmful+' harmful · '+a.unresolved+' unresolved'],['Family posteriors',pct(a.frequency_mean),'6 × Beta(.5+k, .5+n−k)'],['Severity + prior','Four loss bands','$25 / 100 / 500 / 1000'],['Assumed mix','1/6 per family','Fixed challenge weights'],['Weighted binned risk',usd(a.binned_loss_mean_usd)+' / case','Σ weight × probability × severity']];
    const connections=phone?[[[172,55],[198,55]],[[92,90],[92,135]],[[92,205],[150,265]],[[278,205],[245,265]]]:[[[185,57],[235,57]],[[97,95],[97,145]],[[410,57],[490,115]],[[185,182],[490,140]],[[410,182],[490,150]]];
    if(phone)svg('path',{class:'study-edge',d:'M278 90 C370 110 370 230 255 265'},g);
    connections.forEach(([p,q])=>edge(g,p,q,''));
    boxes.forEach(([x,y,w,h],i)=>{svg('rect',{class:'risk-model-box',x,y,width:w,height:h,rx:8},g);svg('text',{class:'risk-model-label',x:x+12,y:y+19,text:content[i][0]},g);svg('text',{class:'risk-model-value',x:x+12,y:y+41,text:content[i][1]},g);svg('text',{class:'risk-model-small',x:x+12,y:y+58,text:content[i][2]},g);});
    const rows=state.study.analysis.comparisons.filter(c=>['raw_memory','retrieval_use','calculations','bundle'].includes(c.kind)&&c.before.startsWith(state.model+'|')&&c.before.endsWith('|'+Number(state.critic)));
    const criticEffect=state.study.analysis.comparisons.find(c=>c.kind==='critic'&&c.before===state.model+'|'+state.setup+'|0');if(criticEffect)rows.push(criticEffect);
    const effects=$('research-effects');clear(effects);effects.setAttribute('viewBox',phone?'0 0 370 385':'0 0 680 300');svg('title',{text:rows.map(r=>effectLabel(r)+': '+pp(r.posterior_frequency_reduction)+'; 95% credible '+range(r.credible95,pp)).join('. ')},effects);
    const extent=Math.min(1,Math.max(.1,Math.ceil(Math.max(...rows.flatMap(r=>r.credible95.map(Math.abs)))*20)/20));
    const X=p=>phone?140+(p/extent+1)*105:260+(p/extent+1)*195;
    svg('line',{class:'effect-zero',x1:X(0),x2:X(0),y1:20,y2:phone?340:255},effects);
    [-1,-.5,0,.5,1].forEach(p=>svg('text',{class:'effect-text',x:X(p*extent),y:phone?370:285,'text-anchor':'middle',text:Number((100*p*extent).toFixed(1))+' pp'},effects));
    rows.forEach((r,i)=>{const y=phone?42+i*65:38+i*48;svg('text',{class:'effect-text',x:5,y:phone?y-19:y+4,text:effectLabel(r)},effects);svg('line',{class:'effect-line',x1:X(r.credible95[0]),x2:X(r.credible95[1]),y1:y,y2:y},effects);svg('circle',{class:'effect-dot',cx:X(r.posterior_frequency_reduction),cy:y,r:4},effects);});
    const details=$('research-effect-detail');clear(details);
    rows.forEach(r=>{const d=el('div',{class:'effect-case'},details);el('strong',{text:effectLabel(r)+' · observed '+pp(r.observed_frequency_reduction)+' reduction'},d);el('div',{text:r.avoided+' harmful proposals avoided · '+r.introduced+' introduced · '+r.resolved_pairs+'/'+r.scheduled_pairs+' matched pairs'},d);el('small',{text:'Posterior reduction '+pp(r.posterior_frequency_reduction)+' [95% credible '+range(r.credible95,pp)+']. '+(r.credible95[0]<=0&&r.credible95[1]>=0?'Interval crosses zero.':'Conditional on stated priors and workload.')},d);el('small',{text:'Task errors fixed / introduced: '+r.task_errors_fixed+' / '+r.task_errors_introduced+'. Observed proposed-loss reduction: '+usd(r.observed_loss_reduction_usd)+' / matched case.'},d);});
    clear($('research-scenarios'));table($('research-scenarios'),['Family','Harm / resolved','Frequency mean','95% credible'],Object.entries(a.cells).map(([f,c])=>[title(f),c.k+' / '+c.n,pct(c.posterior_mean),range(c.credible95)]));
  }
  const effectLabel=r=>({raw_memory:'Raw memory vs none',retrieval_use:'Selected vs raw memory',calculations:'Calculations vs selected',bundle:'Full bundle vs none',critic:'Critic on vs off',model:'Sonnet vs Haiku'}[r.kind]);
  function render(){if(!state.study?.analysis)return;renderWorkflow();renderRisk();}
  function changeView(view){state.view=view;for(const name of ['workflow','risk']){const active=name===view;$('research-'+name).hidden=!active;$('research-'+name+'-tab').setAttribute('aria-selected',String(active));$('research-'+name+'-tab').tabIndex=active?0:-1;}render();}
  function example(kind){
    if(!state.study)return;const changed=(a,b)=>a&&b&&(a.resolved!==b.resolved||a.task_failure!==b.task_failure||a.proposed_loss_cents!==b.proposed_loss_cents);
    const candidates=state.study.cells.filter(c=>c.model===state.model).filter(c=>kind==='critic'?c.memory_mode===state.setup&&changed(c.initial_outcome,c.corrected_outcome):c.memory_mode===(kind==='calculation'?'selected':'raw')&&changed(outcomeFor(c),outcomeFor(state.study.cells.find(x=>x.case_id===c.case_id&&x.model===c.model&&x.memory_mode===(kind==='calculation'?'grounded':'selected')))));
    if(!candidates.length){showDetails('No observed '+kind+' change',[['Selected configuration','No change in task-error status, resolution or proposed unauthorized loss is recorded for the selected setting in the processed cases. This is not proof of equivalence.']]);return;}
    const next=candidates.find(c=>state.study.cases.findIndex(x=>x.id===c.case_id)>state.index)||candidates[0];state.index=state.study.cases.findIndex(c=>c.id===next.case_id);
    if(kind==='critic'){state.critic=true;$('research-critic').value='1';}else state.setup=kind==='calculation'?'grounded':'selected';
    $('research-case').value=state.index;$('research-setup').value=state.setup;render();
  }
  async function load(){
    $('research-refresh').disabled=true;
    try{const r=await fetch('/api/memory-study');if(!r.ok)throw Error('HTTP '+r.status);const data=await r.json();
      if(!data.available){$('research-status').textContent='The fresh study is preparing verified SurrealDB source snapshots. No evaluation result is available yet.';return;}
      const s=data.study;if(!s.analysis){$('research-status').textContent='Experiment '+s.status+'; waiting for the first completed matched case.';return;}
      const first=!state.study;state.study=s;
      // Illustrative opening example only; every scheduled case remains in the aggregate.
      if(first){const failure=s.cells.find(c=>c.model===state.model&&c.memory_mode==='raw'&&c.initial_outcome.proposed_loss_cents>0);if(failure)state.index=s.cases.findIndex(c=>c.id===failure.case_id);}
      const ids=$('research-case');clear(ids);s.cases.forEach((c,i)=>el('option',{value:i,text:String(i+1).padStart(2,'0')+' · '+title(c.family)},ids));ids.value=state.index;
      ['research-model','research-case','research-setup','research-critic'].forEach(id=>$(id).disabled=false);$('research-setup').value=state.setup;$('research-critic').value=String(Number(state.critic));const processed=new Set(s.cells.map(c=>c.case_id)).size;
      $('research-status').classList.remove('error');$('research-status').textContent=s.status+' · '+processed+'/'+s.cases.length+' fresh cases · '+s.budget.requests_reserved+' real model requests · '+usd(s.budget.accounted_estimated_usd)+' estimated token cost · original study kept separate.';render();
    }catch(e){$('research-status').classList.add('error');$('research-status').textContent='Could not refresh results: '+e.message+(state.study?'. Earlier verified results remain displayed.':'');}finally{$('research-refresh').disabled=false;}
  }
  $('research-model').onchange=e=>{state.model=e.target.value;render();};$('research-case').onchange=e=>{state.index=Number(e.target.value);render();};$('research-setup').onchange=e=>{state.setup=e.target.value;render();};$('research-critic').onchange=e=>{state.critic=e.target.value==='1';render();};$('research-refresh').onclick=load;
  $('research-memory-example').onclick=()=>example('memory');$('research-critic-example').onclick=()=>example('critic');$('research-calculation-example').onclick=()=>example('calculation');
  for(const view of ['workflow','risk']){$('research-'+view+'-tab').onclick=()=>changeView(view);$('research-'+view+'-tab').onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const next=e.key==='Home'?'workflow':e.key==='End'?'risk':view==='workflow'?'risk':'workflow';changeView(next);$('research-'+next+'-tab').focus();}};}
  $('research-dialog-close').onclick=()=>$('research-dialog').close();$('research-dialog').onclose=()=>{if(state.returnFocus?.isConnected)state.returnFocus.focus();else{const id=state.returnFocus?.getAttribute('data-node');const target=id?document.querySelector('#research-graph [data-node="'+id+'"]'):null;(target||$('research-methods')).focus();}};
  $('research-methods').onclick=()=>showDetails('Fresh-case design and interpretation',state.study?[['Design',state.study.design.scope],['Attribution',state.study.analysis.memory_interpretation],['Prior and sensitivity',state.study.analysis.prior],['Uncertainty',state.study.analysis.uncertainty],['Frozen registration',state.study.design]]:[['Status','The registered experiment is preparing. Refresh to check for recorded results.']]);
  $('research-bounds').onclick=()=>{
    const a=arm();showDetails('Conservative bounds and missing outcomes',[
      ['Frequency exact upper endpoint',a.exact_upper==null?'Unavailable: a complete fixed batch is required; '+a.resolved+'/'+a.scheduled+' financial outcomes are resolved.':pct(a.exact_upper)+'; simultaneous complete-batch upper bound over 96 family/configuration cells.'],
      ['Conditional proposed-loss interval',range([a.conditional_loss_bound.lower_usd,a.conditional_loss_bound.upper_usd],usd)+' per completed case.'],
      ['Prior sensitivity',range(a.prior_sensitivity_usd,usd)+' per case. This range varies frequency and severity priors; it is not a confidence interval.'],
      ['Missing-outcome sensitivity',a.missing_outcome_mean_range_usd?range(a.missing_outcome_mean_range_usd,usd)+' per processed case, assigning each unknown loss anywhere in $0–$1,000. This is not a confidence interval.':'Unavailable'],
      ['Assumptions and separate error budgets',state.study.analysis.uncertainty]]);
    const host=$('research-dialog-body'),key=state.model+'|'+state.setup+'|'+Number(state.critic);
    el('h3',{text:'Matched contrasts involving this configuration'},host);
    table(host,['Change','Complete pairs','Exact frequency reduction interval','Conditional dollar reduction interval'],state.study.analysis.comparisons.filter(c=>c.before===key||c.after===key).map(c=>{
      const describe=k=>{const p=k.split('|');return modelName(p[0])+' · '+labels[p[1]]+' · critic '+(p[2]==='1'?'on':'off');};
      return [describe(c.before)+' → '+describe(c.after),c.resolved_pairs+'/'+c.scheduled_pairs,range(c.confidence95,pp),range(c.conditional_loss_reduction_bound_usd,usd)+' / matched case'];
    }));
  };
  $('research-all-arms').onclick=()=>{
    showDetails('Haiku and Sonnet · all strategies',[['Interpretation','Same 36 fresh cases; previous cases are excluded. Review adds compute. Selected guidance changes context and use. The full bundle adds visible-record calculations. Separate arm intervals do not establish a model ranking.']]);const host=$('research-dialog-body');
    table(host,['Model / strategy / critic','Harm / resolved','Task errors','Posterior frequency [95% credible]','Observed proposed loss'],Object.values(state.study.analysis.arms).map(a=>[modelName(a.model)+' · '+labels[a.memory_mode]+' · critic '+(a.critic?'on':'off'),a.harmful+' / '+a.resolved,a.task_errors,pct(a.frequency_mean)+' ['+range(a.frequency_credible95)+']',usd(a.observed_loss_usd)]));
    el('h3',{text:'Matched model and critic comparisons'},host);el('p',{text:'Positive model reduction favors Sonnet relative to Haiku. Positive critic reduction favors review. Every row matches the same cases; intervals crossing zero are inconclusive.'},host);
    table(host,['Comparison / strategy','Pairs','Avoided / introduced','Posterior reduction [95% credible]'],state.study.analysis.comparisons.filter(c=>['model','critic'].includes(c.kind)).map(c=>{const parts=c.before.split('|');return [effectLabel(c)+' · '+(c.kind==='critic'?modelName(parts[0])+' · ':'')+labels[parts[1]]+' · critic '+parts[2],c.resolved_pairs+' / '+c.scheduled_pairs,c.avoided+' / '+c.introduced,pp(c.posterior_frequency_reduction)+' ['+range(c.credible95,pp)+']'];}));
  };
  $('research-audit').onclick=async()=>{
    try{const r=await fetch('/api/memory-audit');if(!r.ok)throw Error('HTTP '+r.status);const d=await r.json();showDetails('Why investigate Haiku memory?',[['What the earlier study showed',d.interpretation.join(' ')],['Paired harmful proposals',{without_memory:d.harmful_off_on[0],with_raw_memory:d.harmful_off_on[1],fixed:d.harmful_fixed_introduced[0],introduced:d.harmful_fixed_introduced[1]}],['Recorded changes, not private reasoning',d.paired_changes]]);}catch(e){showDetails('Investigation unavailable',[['Status',e.message]]);}
  };
  addEventListener('resize',render);load();
})();
