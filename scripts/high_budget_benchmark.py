"""Fresh-case higher-output follow-up; combined model allowance stays <= $5."""
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
from app.hardcases import generate_hard, digest, HINTS
from app.hardbench import Agent, MODELS, ResearchBudget, model_call, outcome, summarize, PRICES
from scripts.hard_benchmark import write

ROOT=Path(__file__).resolve().parents[1]


def run(directory):
    primary=json.loads((directory/'hard-benchmark.json').read_text())
    if primary['status']!='complete':raise RuntimeError('Complete and retain the primary study first')
    primary_cost=primary['budget']['accounted_estimated_usd']
    maximum=min(3.,5.-primary_cost)
    if maximum<=0:raise RuntimeError('Combined research cost allowance reached')
    memory=json.loads((directory/'hard-benchmark-memory.json').read_text())
    assert digest(memory)==primary['design']['retrieved_memory_sha256']
    folder=directory/'high-budget';folder.mkdir(exist_ok=True)
    lock=(folder/'study.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    cases=generate_hard(2102147,2)
    sources=['app/hardbench.py','app/hardcases.py','app/providers.py','app/domain.py','app/risk.py','scripts/high_budget_benchmark.py']
    design={'version':'tool-records-high-budget-v1','heldout_seed':2102147,'heldout_repeats':2,
            'phases':{'heldout':{'cases':16,'sha256':digest(cases)}},'models':list(MODELS),'critic_model':MODELS[1],
            'settings':{'max_tokens':2048,'effort':'low','haiku_thinking':'disabled','sonnet_thinking':'between_tools'},
            'memory_sha256':digest(HINTS),'retrieved_memory_sha256':digest(memory),
            'max_requests':128,'max_usd':maximum,'primary_accounted_usd':primary_cost,'combined_max_usd':5.,
            'primary_study_sha256':hashlib.sha256((directory/'hard-benchmark.json').read_bytes()).hexdigest(),
            'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
            'scope':'Separate higher-output validation on 16 new cases of the same eight families. Follow-up motivated by truncation in the primary study; not pooled and not a causal comparison of token budgets because cases and response draws differ.',
            'price_basis_usd_per_million':PRICES}
    budget=ResearchBudget(str(folder/'requests.sqlite3'),maximum,128);budget.pin(design)
    write(folder/'design.json',design)
    report={'schema_version':'hard-factorial-v1','phase':'heldout','design':design,'cases':cases,'memory':memory,
            'cells':[],'status':'running','budget':budget.totals(),'simulation_only':True}
    path=folder/'hard-benchmark.json';write(path,report);agent=Agent()
    def cell(index,case,model,use_memory):
        recalled=memory['families'][case['family']]['hits'] if use_memory else []
        key='high-budget:'+case['id']+':'+model+':'+str(use_memory)
        initial=model_call(agent,budget,case['observation'],recalled,model,key=key+':proposer',max_tokens=2048)
        corrected=(model_call(agent,budget,case['observation'],recalled,MODELS[1],original=initial['proposal'],key=key+':critic',max_tokens=2048)
                   if initial['status']=='complete' else {'status':'not_started','code':'initial_proposal_unavailable','usage':{'input_tokens':0,'output_tokens':0}})
        return {'case_id':case['id'],'index':index,'family':case['family'],'model':model,'memory':use_memory,
                'initial':initial,'initial_outcome':outcome(case,initial),'corrected':corrected,'corrected_outcome':outcome(case,corrected)}
    try:
        with ThreadPoolExecutor(4) as pool:
            for index,case in enumerate(cases):
                arms=[(m,v) for m in MODELS for v in (False,True)];random.Random(2102151+index).shuffle(arms)
                for f in as_completed([pool.submit(cell,index,case,m,v) for m,v in arms]):report['cells'].append(f.result())
                report['cells'].sort(key=lambda c:(c['index'],c['model'],c['memory']))
                report['analysis']=summarize(cases,report['cells']);report['budget']=budget.totals()
                report['combined_accounted_usd']=primary_cost+report['budget']['accounted_estimated_usd']
                write(path,report)
                print(json.dumps({'case':index+1,'total':len(cases),'budget':report['budget'],'combined_estimated_usd':report['combined_accounted_usd']}),flush=True)
                if any(c[s]['status']=='provider_error' for c in report['cells'] for s in ('initial','corrected')):
                    report['status']='provider_error';write(path,report);raise SystemExit(2)
        report['status']='complete';write(path,report)
    except Exception as exc:
        report['status']='paused';report['error_type']=type(exc).__name__;write(path,report);raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,default=Path(os.getenv('DATABASE_PATH','data/riskgraph.sqlite3')).parent)
    run(parser.parse_args().directory)
