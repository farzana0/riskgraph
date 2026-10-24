"""Travel experiment and shared-budget live replay support."""
import argparse,fcntl,hashlib,json,os,sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.travel import generate,VERSION,outcome
from app.travel_calls import call,TravelBudget
from app.travel_stats import analyze
from app.hardcases import digest
from app.hardbench import ResearchBudget,PRICES
from app.providers import Agent,MODELS
from scripts.hard_benchmark import write
ROOT=Path(__file__).resolve().parents[1]
SOURCES=['app/travel.py','app/travel_calls.py','app/travel_stats.py','scripts/travel_study.py','app/hardbench.py','app/providers.py','app/risk.py','app/research_stats.py']


def registration():
    return {'version':VERSION,'seed':2026102453,'cases':32,'cases_sha256':digest(generate()),'models':list(MODELS),'critic_model':MODELS[1],'max_usd':1.2,'max_requests':256,'study_max_requests':128,'settings':{'max_tokens':1024,'effort':'low'},'prices':PRICES,'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},'scope':'32 fresh synthetic trips, eight families. Two initial models, one separate Sonnet corrective review per valid proposal. No memory intervention. Synthetic loss uses supplied cancellation penalties or nonrefundable full charges. Study and later live demo share the same persistent US$1.20 allowance and 256-request cap. No automatic retry; source hashes and all cases frozen before calls.'}


def execute(directory,case,model,key,notify=None):
    budget=TravelBudget(str(directory/'requests.sqlite3'),1.2,256);agent=Agent()
    try:initial=call(agent,budget,case['observation'],model,key+':initial')
    except RuntimeError:initial={'status':'not_started','code':'budget_or_unknown'}
    row={'case_id':case['id'],'family':case['family'],'model':model,'initial':initial,'initial_outcome':outcome(case,initial)}
    if notify:notify({**row,'status':'reviewing'})
    try:corrected=call(agent,budget,case['observation'],MODELS[1],key+':critic',initial['proposal']) if initial['status']=='complete' else {'status':'not_started','code':'initial_proposal_unavailable'}
    except RuntimeError:corrected={'status':'not_started','code':'budget_or_unknown'}
    row.update(corrected=corrected,corrected_outcome=outcome(case,corrected));return row


def run(directory):
    directory.mkdir(parents=True,exist_ok=True);lock=(directory/'study.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    design=registration();assert json.loads(json.dumps(design))==json.loads((ROOT/'docs/examples/travel-v1-preregistration.json').read_text());cases=generate();budget=TravelBudget(str(directory/'requests.sqlite3'),1.2,256);budget.pin(design)
    s={'schema_version':VERSION,'design':design,'cases':cases,'cells':[],'status':'running','budget':budget.totals()};path=directory/'study.json';write(path,s)
    try:
        with ThreadPoolExecutor(2) as pool:
            for c in cases:
                rows=list(pool.map(lambda model:execute(directory,c,model,VERSION+':'+c['id']+':'+model),MODELS));s['cells'].extend(rows);s['budget']=budget.totals();s['analysis']=analyze(s);write(path,s);print(json.dumps({'cases':len(s['cells'])//2,'budget':s['budget']}),flush=True)
                if any(r[stage]['status']=='provider_error' for r in rows for stage in ('initial','corrected')):s['status']='provider_error';write(path,s);return
                if any(r[stage].get('code')=='budget_or_unknown' for r in rows for stage in ('initial','corrected')):s['status']='budget_limited';write(path,s);return
        s['status']='complete';s['analysis']=analyze(s);write(path,s)
    except BaseException as exc:s['status']='budget_limited' if isinstance(exc,RuntimeError) else 'paused';s['error_type']=type(exc).__name__;s['budget']=budget.totals();write(path,s);raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--register',action='store_true');p.add_argument('--directory',type=Path,default=Path(os.getenv('DATABASE_PATH','data/riskgraph.sqlite3')).parent/'travel-v1');a=p.parse_args()
    if a.register:write(ROOT/'docs/examples/travel-v1-preregistration.json',registration());print('Travel protocol saved; no paid calls')
    else:run(a.directory)
