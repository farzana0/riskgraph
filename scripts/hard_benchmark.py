"""Explicitly budgeted factorial benchmark, run on Render with existing keys.

No payment tools, no production counter reset, no response-conditioned retries.
Both phases, all cases and all prompts are pinned before the first paid call.
"""
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
from app.hardcases import generate_hard, VERSION, HINTS, MEMORY_TAG, digest
from app.hardbench import Agent, MODELS, ResearchBudget, model_call, outcome, summarize, PROMPT, CRITIC, PRICES
from app.providers import AgentMemory, failure_details
import httpx

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['app/hardcases.py','app/hardbench.py','scripts/hard_benchmark.py','app/domain.py','app/risk.py','app/providers.py']


def write(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value,indent=2)+'\n')
    temp.replace(path)


def frozen_memory(path):
    if path.exists():
        saved = json.loads(path.read_text())
        if saved.get('hint_sha256') != digest(HINTS):
            raise ValueError('Memory bank changed; use a new study version')
    else:
        saved = {'version':VERSION,'hint_sha256':digest(HINTS),'families':{}}
    memory = AgentMemory()
    if not memory.configured:
        raise RuntimeError('Hosted memory is required for this experiment; no local substitute')
    for family, text in HINTS.items():
        if family in saved['families']:
            continue
        body = {'text':MEMORY_TAG+' procedural prior '+family+': '+text,'infer':'full','scopes':[[memory.scope]]}
        stored = memory._post('/facts',body,'hard-prior-'+VERSION+'-'+family)
        result = memory._post('/query',{'query':MEMORY_TAG+' procedural prior '+family,'k':4,'lens':[[memory.scope]],'scopeView':'strict','mode':'hybrid'})
        hits = [{"id":h.get('id'),"text":str(h.get('text',''))[:1800]} for h in result.get('hits',[]) if MEMORY_TAG in str(h.get('text','')) and family in str(h.get('text',''))]
        trace = result.get('trace',{}).get('traceId')
        if not hits or not trace:
            raise RuntimeError('Prior bank retrieval has no matching sources or trace; no paid calls started')
        saved['families'][family] = {'hits':hits[:2],'trace_id':trace,'write_turn_id':stored.get('turnId'),'prior_text':body['text']}
        write(path,saved)
        print(json.dumps({'memory_family':family,'hits':len(hits[:2]),'trace':True}),flush=True)
    return saved


def run(args):
    if not os.getenv('ANTHROPIC_API_KEY'):
        raise RuntimeError('Provider not configured')
    args.directory.mkdir(parents=True,exist_ok=True)
    lock = (args.directory/'hard-benchmark.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    cases_by_phase = {'development':generate_hard(2102131,1),'heldout':generate_hard(2102137,4)}
    design = {'version':VERSION,'phases':{p:{'cases':len(c),'sha256':digest(c)} for p,c in cases_by_phase.items()},
              'proposer_prompt':PROMPT,'critic_prompt':CRITIC,'models':list(MODELS),'critic_model':MODELS[1],
              'max_usd':args.max_usd,'max_requests':320,'memory_sha256':digest(HINTS),
              'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
              'settings':{'max_tokens':900,'effort':'low','haiku_thinking':'disabled','sonnet_thinking':'between_tools'},
              'price_basis_usd_per_million':PRICES,'ordering_seed':2102141,
              'scope':'Development phase is contract checking, excluded from held-out results. No prompt, case or memory changes between phases. Four matched model/memory cells per case, each followed by the same Sonnet corrective critic. All proposals scored with the independent gate.'}
    budget = ResearchBudget(str(args.directory/'hard-benchmark.sqlite3'),args.max_usd,320)
    # Both phases are archived before any paid request and never enter a model.
    write(args.directory/'hard-benchmark-cases.json',cases_by_phase)
    memory = frozen_memory(args.directory/'hard-benchmark-memory.json')
    design['retrieved_memory_sha256'] = digest(memory)
    budget.pin(design)
    write(args.directory/'hard-benchmark-design.json',design)
    cases = cases_by_phase[args.phase]
    path = args.directory/('hard-benchmark.json' if args.phase=='heldout' else 'hard-benchmark-development.json')
    report = {'schema_version':'hard-factorial-v1','phase':args.phase,'design':design,'cases':cases,'cells':[],
              'memory':memory,'status':'running','budget':budget.totals(),'simulation_only':True}
    write(path,report)
    agent = Agent()
    def cell(index,case,model,use_memory):
        key = args.phase+':'+case['id']+':'+model+':'+str(use_memory)
        recalled = memory['families'][case['family']]['hits'] if use_memory else []
        initial = model_call(agent,budget,case['observation'],recalled,model,key=key+':proposer')
        row = {'case_id':case['id'],'family':case['family'],'index':index,'model':model,'memory':use_memory,
               'initial':initial,'initial_outcome':outcome(case,initial)}
        if initial['status']=='complete':
            corrected = model_call(agent,budget,case['observation'],recalled,MODELS[1],original=initial['proposal'],key=key+':critic')
        else:
            corrected = {'status':'not_started','code':'initial_proposal_unavailable','usage':{'input_tokens':0,'output_tokens':0}}
        row.update(corrected=corrected,corrected_outcome=outcome(case,corrected))
        return row
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            for index,case in enumerate(cases):
                cells = [(m,use) for m in MODELS for use in (False,True)]
                random.Random(2102141+index).shuffle(cells)
                futures = [pool.submit(cell,index,case,m,use) for m,use in cells]
                for future in as_completed(futures):
                    report['cells'].append(future.result())
                report['cells'].sort(key=lambda c:(c['index'],c['model'],c['memory']))
                report['budget']=budget.totals()
                report['analysis']=summarize(cases,report['cells'])
                write(path,report)
                print(json.dumps({'phase':args.phase,'case':index+1,'total':len(cases),'family':case['family'],
                                  'requests':report['budget']['requests_reserved'],'estimated_usd':report['budget']['accounted_estimated_usd'],
                                  'task_failures':[a['task_failures'] for a in report['analysis']['arms']],
                                  'harmful_proposals':[a['harmful_proposals'] for a in report['analysis']['arms']]}),flush=True)
                if any(c['initial']['status']=='provider_error' or c['corrected']['status']=='provider_error' for c in report['cells']):
                    report['status']='provider_error';write(path,report);raise SystemExit(2)
        report['status']='complete'
    except Exception as exc:
        report['status']='paused'
        report['error_type']=type(exc).__name__
        write(path,report)
        raise
    report['budget']=budget.totals()
    write(path,report)
    print(json.dumps({'phase':args.phase,'status':'complete','budget':report['budget']}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--phase',choices=['development','heldout'],required=True)
    parser.add_argument('--directory',type=Path,default=Path(os.getenv('DATABASE_PATH','data/riskgraph.sqlite3')).parent)
    parser.add_argument('--max-usd',type=float,default=5.)
    run(parser.parse_args())
