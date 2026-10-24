"""Registered, budget-limited replication with persistent case and request caches."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.hardcases import digest
from app.hardbench import ResearchBudget, outcome, PRICES
from app.providers import Agent, MODELS
from app.followup_cases import VERSION, SEED, FAMILIES, generate
from app.followup_stats import MODES, analyze, precision
from app.memory_workflow import BANK, USE_CONTRACT, context, plan
from app.memory_calls import payload, call
from app.record_tools import calculate
from scripts.hard_benchmark import write

ROOT=Path(__file__).resolve().parents[1]
SOURCES=['app/followup_cases.py','app/followup_stats.py','scripts/followup_study.py','app/memory_cases.py','app/memory_workflow.py','app/record_tools.py','app/memory_calls.py','app/hardbench.py','app/hardcases.py','app/providers.py','app/domain.py','app/research_stats.py','app/risk.py']


def registration(per_family=16, max_usd=5.):
    cases=generate(per_family)
    if not 0 < max_usd <= 15: raise ValueError('Invalid new allowance')
    prior=ROOT/'docs/examples/memory-v3.json'
    snapshot=json.loads(prior.read_text())['memory']
    return {'version':VERSION,'seed':SEED,'per_family':per_family,'cases':len(cases),'cases_sha256':digest(cases),'families':list(FAMILIES),
        'memory_modes':list(MODES),'models':list(MODELS),'critic_model':MODELS[1], 'max_usd':max_usd,'max_requests':len(cases)*8,
        'settings':{'max_tokens':2048,'effort':'low','haiku_thinking':'disabled','sonnet_thinking':'between_tools'},
        'ordering_seed':2026102443,'price_basis_usd_per_million':PRICES,'previous_study_sha256':hashlib.sha256(prior.read_bytes()).hexdigest(),
        'retrieved_memory_sha256':digest(snapshot),'bank_sha256':digest(BANK),'use_contract_sha256':digest(USE_CONTRACT),
        'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
        'scope':'Fresh independent draws from the unchanged hardest UTC, reversal-chain and approval-total generator families. Regression enrichment chosen from the earlier study, not a representative workload. Two strategies (none, selected memory), two models, separate Sonnet critic on/off. No arithmetic support in model inputs. The actual SurrealDB snapshot and prompts are held fixed; no fresh retrieval or memory writes. Earlier observations are excluded. Fixed sample and spending allowance registered before responses; incomplete cases and any provider failure remain explicit. No paid retries.'}


def run(directory):
    if not os.getenv('ANTHROPIC_API_KEY'):raise RuntimeError('Provider not configured')
    registered=json.loads((ROOT/'docs/examples/memory-v4-preregistration.json').read_text())
    assert registered==json.loads(json.dumps(registration(registered['per_family'],registered['max_usd'])))
    directory.mkdir(parents=True,exist_ok=True)
    lock=(directory/'study.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    design=registered;cases=generate(design['per_family']);memory=json.loads((ROOT/'docs/examples/memory-v3.json').read_text())['memory']
    prepared={c['id']:{'plan':plan(c['observation']),'selected_context':context(c['observation'],memory),'calculations':calculate(c['observation'])} for c in cases}
    design={**design,'prepared_sha256':digest(prepared)}
    budget=ResearchBudget(str(directory/'requests.sqlite3'),design['max_usd'],design['max_requests']);budget.pin(design)
    s={'schema_version':'memory-regression-v4','design':design,'cases':cases,'memory':memory,'prepared':prepared,'cells':[],'status':'running','budget':budget.totals(),'simulation_only':True}
    path=directory/'study.json';agent=Agent()
    def cell(index,c,model,mode):
        cache=directory/'cells'/('-%s-%s-%s.json'%(c['id'],model,mode));cache.parent.mkdir(exist_ok=True)
        if cache.exists():return json.loads(cache.read_text())
        recalled=[] if mode=='none' else prepared[c['id']]['selected_context'];k=VERSION+':'+c['id']+':'+model+':'+mode
        result={'case_id':c['id'],'index':index,'family':c['family'],'model':model,'memory_mode':mode,
                'context_sha256':digest(recalled),'calculation_sha256':None}
        try:
            initial=call(agent,budget,payload(c['observation'],recalled,model,mode),k+':initial')
        except RuntimeError as exc:
            return {**result,'initial':{'status':'not_started','code':'budget_or_unknown'},'initial_outcome':outcome(c,{'status':'not_started'}),'corrected':{'status':'not_started','code':'initial_proposal_unavailable'},'corrected_outcome':outcome(c,{'status':'not_started'})}
        try:
            corrected=call(agent,budget,payload(c['observation'],recalled,MODELS[1],mode,original=initial['proposal']),k+':critic') if initial['status']=='complete' else {'status':'not_started','code':'initial_proposal_unavailable'}
        except RuntimeError:
            corrected={'status':'not_started','code':'budget_or_unknown'}
        result.update(initial=initial,initial_outcome=outcome(c,initial),corrected=corrected,corrected_outcome=outcome(c,corrected))
        # Unstarted budget-limited stages can resume against the same request ledger.
        if corrected.get('code')!='budget_or_unknown':write(cache,result)
        return result
    write(path,s)
    try:
        with ThreadPoolExecutor(4) as pool:
            for index,c in enumerate(cases):
                arms=[(m,mode) for m in MODELS for mode in MODES];random.Random(2026102443+index).shuffle(arms)
                # Keep every scheduled cell, even if one cannot start within the allowance.
                rows=list(pool.map(lambda pair:cell(index,c,*pair),arms));s['cells'].extend(rows)
                s['cells'].sort(key=lambda c:(c['index'],c['model'],c['memory_mode']));s['budget']=budget.totals();s['analysis']=analyze(s);write(path,s)
                print(json.dumps({'case':index+1,'total':len(cases),'family':c['family'],'budget':s['budget']}),flush=True)
                if any(r[stage]['status']=='provider_error' for r in rows for stage in ('initial','corrected')):
                    s['status']='provider_error';write(path,s);return
                if any(r[stage].get('code')=='budget_or_unknown' for r in rows for stage in ('initial','corrected')):
                    s['status']='budget_limited';write(path,s);return
        s['status']='complete';s['analysis']=analyze(s);s['precision']=precision(s);write(path,s)
    except BaseException as exc:
        s['status']='paused';s['error_type']=type(exc).__name__;s['budget']=budget.totals();write(path,s);raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--register',action='store_true');p.add_argument('--per-family',type=int,default=16);p.add_argument('--max-usd',type=float,default=5.);p.add_argument('--directory',type=Path,default=Path(os.getenv('DATABASE_PATH','data/riskgraph.sqlite3')).parent/'memory-v4');args=p.parse_args()
    if args.register:write(ROOT/'docs/examples/memory-v4-preregistration.json',registration(args.per_family,args.max_usd));print('Registration saved; no paid requests')
    else:run(args.directory)
