"""Budgeted, resumable real-provider factorial experiment; no payment tools."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.research_cases import VERSION,SEED,HINTS,generate
from app.hardcases import digest
from app.hardbench import Agent,MODELS,ResearchBudget,model_call,outcome,summarize,PRICES
from app.providers import AgentMemory
from scripts.hard_benchmark import write

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['app/research_cases.py','app/research_stats.py','scripts/research_study.py','app/hardbench.py','app/providers.py','app/domain.py']


def registration():
    cases = generate()
    return {'version':VERSION,'seed':SEED,'cases':len(cases),'cases_sha256':digest(cases),'memory_hint_sha256':digest(HINTS),
        'models':list(MODELS),'critic_model':MODELS[1],'max_usd':5.,'max_requests':len(cases)*8,
        'settings':{'max_tokens':2048,'effort':'low','haiku_thinking':'disabled','sonnet_thinking':'between_tools'},
        'price_basis_usd_per_million':PRICES,'ordering_seed':2026102403,
        'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
        'scope':'Fresh 48-case, 12-family balanced challenge; all cases, scoring rules, memory hints, prompts and analysis fixed before paid responses. Four model/memory cells per case; critic/no-critic share the exact initial proposal. No test-outcome writeback or result-dependent selection. Separate from historical experiments.'}


def frozen_memory(path):
    if path.exists():
        saved=json.loads(path.read_text())
        if saved['hint_sha256']!=digest(HINTS):raise ValueError('Frozen memory changed')
    else:saved={'version':VERSION,'hint_sha256':digest(HINTS),'families':{}}
    memory=AgentMemory()
    if not memory.configured:raise RuntimeError('Actual hosted SurrealDB memory is required')
    tag='RGCOMPOUND20261024V2'
    for family,text in HINTS.items():
        if family in saved['families']:continue
        stored=memory._post('/facts',{'text':tag+' procedural prior '+family+': '+text,'infer':'full','scopes':[[memory.scope]]},tag+'-'+family)
        result=memory._post('/query',{'query':tag+' procedural prior '+family,'k':5,'lens':[[memory.scope]],'scopeView':'strict','mode':'hybrid'})
        hits=[{'id':h.get('id'),'text':str(h.get('text',''))[:2400]} for h in result.get('hits',[]) if tag in str(h.get('text','')) and family in str(h.get('text',''))]
        trace=result.get('trace',{}).get('traceId')
        if not hits or not trace:raise RuntimeError('Missing matching SurrealDB source or retrieval trace; no paid calls started')
        saved['families'][family]={'hits':hits[:2],'trace_id':trace,'write_turn_id':stored.get('turnId'),'prior_text':text}
        write(path,saved);print(json.dumps({'memory_family':family,'source_hits':len(hits[:2]),'retrieval_trace':True}),flush=True)
    return saved


def run(directory):
    from app.research_stats import analyze
    if not os.getenv('ANTHROPIC_API_KEY'):raise RuntimeError('Provider key unavailable')
    directory.mkdir(parents=True,exist_ok=True)
    lock=(directory/'study.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    design=registration();cases=generate()
    memory=frozen_memory(directory/'memory.json');design['retrieved_memory_sha256']=digest(memory)
    budget=ResearchBudget(str(directory/'requests.sqlite3'),design['max_usd'],design['max_requests']);budget.pin(design)
    write(directory/'design.json',design)
    report={'schema_version':'real-memory-study-v2','design':design,'cases':cases,'memory':memory,'cells':[],'status':'running','budget':budget.totals(),'simulation_only':True}
    path=directory/'study.json';write(path,report);agent=Agent()
    def cell(index,case,model,use_memory):
        recalled=memory['families'][case['family']]['hits'] if use_memory else []
        key=VERSION+':'+case['id']+':'+model+':'+str(use_memory)
        initial=model_call(agent,budget,case['observation'],recalled,model,key=key+':initial',max_tokens=2048)
        corrected=(model_call(agent,budget,case['observation'],recalled,MODELS[1],original=initial['proposal'],key=key+':critic',max_tokens=2048)
            if initial['status']=='complete' else {'status':'not_started','code':'initial_proposal_unavailable'})
        return {'case_id':case['id'],'index':index,'family':case['family'],'model':model,'memory':use_memory,
            'memory_trace_id':memory['families'][case['family']]['trace_id'] if use_memory else None,
            'initial':initial,'initial_outcome':outcome(case,initial),'corrected':corrected,'corrected_outcome':outcome(case,corrected)}
    try:
        with ThreadPoolExecutor(4) as pool:
            for index,case in enumerate(cases):
                arms=[(m,v) for m in MODELS for v in (False,True)];random.Random(2026102403+index).shuffle(arms)
                for future in as_completed([pool.submit(cell,index,case,m,v) for m,v in arms]):report['cells'].append(future.result())
                report['cells'].sort(key=lambda c:(c['index'],c['model'],c['memory']))
                report['budget']=budget.totals();report['analysis']=analyze(report)
                write(path,report)
                print(json.dumps({'case':index+1,'total':len(cases),'family':case['family'],'budget':report['budget']}),flush=True)
                if any(c[s]['status']=='provider_error' for c in report['cells'] for s in ('initial','corrected')):
                    report['status']='provider_error';write(path,report);return
        report['status']='complete';report['analysis']=analyze(report);write(path,report)
    except BaseException as exc:
        report['status']='paused';report['error_type']=type(exc).__name__;report['budget']=budget.totals();write(path,report);raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--register',action='store_true');parser.add_argument('--directory',type=Path,default=Path(os.getenv('DATABASE_PATH','data/riskgraph.sqlite3')).parent/'research-v2')
    args=parser.parse_args()
    if args.register:
        write(ROOT/'docs/examples/research-v2-preregistration.json',registration());print('Frozen registration saved; no provider calls')
    else:run(args.directory)
