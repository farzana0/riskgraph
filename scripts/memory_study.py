"""Prospective memory ablation on fresh cases; run only in the configured service."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.hardcases import digest
from app.hardbench import ResearchBudget,outcome,PRICES
from app.providers import Agent,AgentMemory,MODELS
from app.memory_cases import VERSION,SEED,FAMILIES,generate
from app.memory_workflow import TAG,BANK,USE_CONTRACT,fact_text,select,context,plan
from app.memory_calls import payload,call
from app.memory_stats import MODES,LABELS,analyze
from app.record_tools import calculate
from scripts.hard_benchmark import write

ROOT=Path(__file__).resolve().parents[1]
SOURCES=['app/memory_cases.py','app/memory_workflow.py','app/record_tools.py','app/memory_calls.py','app/memory_stats.py','scripts/memory_study.py','app/hardbench.py','app/hardcases.py','app/providers.py','app/domain.py','app/research_stats.py','app/risk.py']


def registration():
    cases=generate();old=ROOT/'docs/examples/research-v2.json'
    return {'version':VERSION,'seed':SEED,'cases':len(cases),'cases_sha256':digest(cases),'families':list(FAMILIES),
        'memory_modes':list(MODES),'mode_labels':LABELS,'models':list(MODELS),'critic_model':MODELS[1],
        'bank_sha256':digest(BANK),'use_contract_sha256':digest(USE_CONTRACT),'max_usd':6.,'max_requests':len(cases)*16,
        'settings':{'max_tokens':2048,'effort':'low','haiku_thinking':'disabled','sonnet_thinking':'between_tools'},
        'ordering_seed':2026102419,'price_basis_usd_per_million':PRICES,'previous_study_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),
        'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
        'scope':'36 new, harder targeted cases; six equal-weight families. Four memory strategies, each with and without the same separate Sonnet critic, for each model. Critic-off reuses the initial proposal. Raw-versus-selected tests retrieval/representation/usage jointly; selected-versus-grounded adds visible-record deterministic calculations. No scoring oracle enters any request. Previous outcomes are development evidence only, not pooled.'}


def freeze(directory,cases):
    path=directory/'memory.json'
    if path.exists():
        saved=json.loads(path.read_text())
        if saved['bank_sha256']!=digest(BANK) or saved['cases_sha256']!=digest(cases):raise ValueError('Frozen memory or cases changed')
    else:saved={'bank_sha256':digest(BANK),'cases_sha256':digest(cases),'raw':{},'skills':{}}
    memory=AgentMemory()
    if not memory.configured:raise RuntimeError('Actual hosted memory required; no local substitute')
    for family in FAMILIES:
        if family in saved['raw']:continue
        result=memory._post('/query',{'query':'RGCOMPOUND20261024V2 procedural prior '+family,'k':5,'lens':[[memory.scope]],'scopeView':'strict','mode':'hybrid'})
        hits=[{'id':h.get('id'),'text':str(h.get('text',''))[:2400]} for h in result.get('hits',[]) if 'RGCOMPOUND20261024V2' in str(h.get('text','')) and family in str(h.get('text',''))]
        trace=result.get('trace',{}).get('traceId')
        if not hits or not trace:raise RuntimeError('Missing raw-memory control source or trace')
        saved['raw'][family]={'hits':hits[:2],'trace_id':trace};write(path,saved)
    for skill in BANK:
        if skill in saved['skills']:continue
        stored=memory._post('/facts',{'text':fact_text(skill),'infer':'full','scopes':[[memory.scope]]},TAG+'-'+skill)
        response=memory._post('/query',{'query':TAG+' '+skill+' '+digest(BANK[skill]),'k':8,'lens':[[memory.scope]],'scopeView':'strict','mode':'hybrid'})
        selected=select(skill,response);selected['write_turn_id']=stored.get('turnId');saved['skills'][skill]=selected;write(path,saved)
        print(json.dumps({'verified_skill':skill,'accepted':len(selected['selected']),'rejected':len(selected['rejected']),'trace':True}),flush=True)
    return saved


def run(directory):
    if not os.getenv('ANTHROPIC_API_KEY'):raise RuntimeError('Provider not configured')
    directory.mkdir(parents=True,exist_ok=True);lock=(directory/'study.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    design=registration();cases=generate();memory=freeze(directory,cases);design['retrieved_memory_sha256']=digest(memory)
    prepared={c['id']:{'plan':plan(c['observation']),'selected_context':context(c['observation'],memory),'calculations':calculate(c['observation'])} for c in cases}
    # Input-derived calculations must be auditable; unresolved results remain explicit.
    design['prepared_sha256']=digest(prepared);budget=ResearchBudget(str(directory/'requests.sqlite3'),6.,len(cases)*16);budget.pin(design);write(directory/'design.json',design)
    s={'schema_version':'memory-ablation-v3','design':design,'cases':cases,'memory':memory,'prepared':prepared,'cells':[],'status':'running','budget':budget.totals(),'simulation_only':True}
    path=directory/'study.json';write(path,s);agent=Agent()
    def cell(index,c,model,mode):
        obs=c['observation'];prep=prepared[c['id']]
        recalled=[] if mode=='none' else memory['raw'][c['family']]['hits'] if mode=='raw' else prep['selected_context']
        calculations=prep['calculations'] if mode=='grounded' else None
        k=VERSION+':'+c['id']+':'+model+':'+mode
        initial=call(agent,budget,payload(obs,recalled,model,mode,calculations),k+':initial')
        corrected=call(agent,budget,payload(obs,recalled,MODELS[1],mode,calculations,initial['proposal']),k+':critic') if initial['status']=='complete' else {'status':'not_started','code':'initial_proposal_unavailable'}
        return {'case_id':c['id'],'index':index,'family':c['family'],'model':model,'memory_mode':mode,
            'initial':initial,'initial_outcome':outcome(c,initial),'corrected':corrected,'corrected_outcome':outcome(c,corrected),
            'context_sha256':digest(recalled),'calculation_sha256':digest(calculations) if calculations else None}
    try:
        with ThreadPoolExecutor(8) as pool:
            for index,c in enumerate(cases):
                arms=[(m,mode) for m in MODELS for mode in MODES];random.Random(2026102419+index).shuffle(arms)
                for future in as_completed([pool.submit(cell,index,c,m,mode) for m,mode in arms]):s['cells'].append(future.result())
                s['cells'].sort(key=lambda c:(c['index'],c['model'],c['memory_mode']));s['budget']=budget.totals();s['analysis']=analyze(s);write(path,s)
                print(json.dumps({'case':index+1,'total':len(cases),'family':c['family'],'budget':s['budget']}),flush=True)
                if any(c[stage]['status']=='provider_error' for c in s['cells'] for stage in ('initial','corrected')):
                    s['status']='provider_error';write(path,s);return
        s['status']='complete';s['analysis']=analyze(s);write(path,s)
    except BaseException as exc:
        s['status']='paused';s['error_type']=type(exc).__name__;s['budget']=budget.totals();write(path,s);raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--register',action='store_true');p.add_argument('--directory',type=Path,default=Path(os.getenv('DATABASE_PATH','data/riskgraph.sqlite3')).parent/'memory-v3');args=p.parse_args()
    if args.register:write(ROOT/'docs/examples/memory-v3-preregistration.json',registration());print('Registration saved; no provider calls')
    else:run(args.directory)
