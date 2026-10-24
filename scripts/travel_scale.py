"""Fresh Haiku scale campaign; frozen source and spend cap, rate limited."""
import argparse,fcntl,gzip,hashlib,json,os,sys,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.travel import generate,outcome
from app.scale_calls import call
from app.travel_scale import summarize,analyze
from app.hardbench import ResearchBudget
from app.providers import Agent,MODELS
from app.hardcases import digest
from scripts.hard_benchmark import write
ROOT=Path(__file__).resolve().parents[1]
VERSION='travel-haiku-scale-v1'

def generate_scale():
    cases=generate(2026102481,688)
    for c in cases:c['id']='scale-'+c['id']
    return cases
SOURCES=['app/travel.py','app/travel_calls.py','app/scale_calls.py','app/travel_scale.py','scripts/travel_scale.py','app/hardbench.py','app/providers.py','app/risk.py','app/research_stats.py','app/hardcases.py','app/domain.py','requirements.txt']


def registration():
    cases=generate_scale()
    return {'version':VERSION,'seed':2026102481,'per_family':688,'cases':5504,'cases_sha256':digest(cases),'model':MODELS[0],'max_usd':2.,'max_requests':5504,'reference_cases':0,'reference_registration_sha256':hashlib.sha256((ROOT/'docs/examples/travel-v1-preregistration.json').read_bytes()).hexdigest(),'settings':{'max_tokens':512,'tool_choice':'forced propose_booking','effort':'low','rate_per_second':8,'workers':24},'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},'scope':'5504 fresh Haiku-only episodes under the same task policy and generator, with a new seed and forced tool response format (512 tokens). No earlier responses are reused or pooled. Format control differs from the original matched study and is not a model-ranking intervention. No critic, no memory, no selection by observed effect. Equal eight-family weights. A new independent US$2 cap makes all new experiment allowances total at most US$8 (refund 4.8, travel/live 1.2, scale 2). Earlier counters remain intact. Unavailable results are never retried or assigned a fabricated proposal loss. This campaign cannot support an unmatched Sonnet comparison.'}


def run(directory):
    d=registration();assert json.loads(json.dumps(d))==json.loads((ROOT/'docs/examples/travel-scale-preregistration.json').read_text())
    directory.mkdir(parents=True,exist_ok=True);lock=(directory/'study.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    reference=Path(os.getenv('DATABASE_PATH','data/riskgraph.sqlite3')).parent/'travel-v1/study.json'
    if not reference.exists():reference=ROOT/'docs/examples/travel-v1.json'
    old=json.loads(reference.read_text());assert old['status']=='complete' and old['design']['cases_sha256']==digest(generate())
    d={**d,'reference_study_sha256':hashlib.sha256(reference.read_bytes()).hexdigest()};cases=generate_scale();byid={c['id']:c for c in cases};prior={c['id']:c for c in old['cases']}
    budget=ResearchBudget(str(directory/'requests.sqlite3'),2.,5504);budget.pin(d);rows={};archive=directory/'responses.jsonl'
    if archive.exists():
        for line in archive.read_text().splitlines():
            r=json.loads(line);assert r['case_id'] not in rows;rows[r['case_id']]=r
    agent=Agent();pacer=Lock();next_time=[0.]
    def evaluate(c):
        with pacer:
            delay=max(0,next_time[0]-time.monotonic())
            if delay:time.sleep(delay)
            next_time[0]=time.monotonic()+.125
        try:r=call(agent,budget,c['observation'],MODELS[0],VERSION+':'+c['id']+':initial')
        except RuntimeError:return None
        return {'case_id':c['id'],'family':c['family'],'model':MODELS[0],'initial':r,'initial_outcome':outcome(c,r),'source':'fresh-scale-request'}
    def report(status):
        data={'schema_version':VERSION,'design':d,'status':status,'processed_cases':len(rows),'scheduled_cases':len(cases),'budget':budget.totals(),**summarize(cases,list(rows.values()),status=='complete')}
        if status=='complete':
            data['precision']=[]
            for per in (4,16,64,256,688):
                subset=[c for c in cases if int(c['id'].rsplit('-',1)[1])<=per];rs=[rows[c['id']] for c in subset];a=analyze(subset,rs)['arms'][MODELS[0]+'|0'];data['precision'].append({'cases':len(subset),'resolved':a['resolved'],'tail':a['tail']})
            data['responses_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
        write(directory/'study.json',data)
    report('running');todo=[c for c in cases if c['id'] not in rows]
    with ThreadPoolExecutor(24) as pool:
        for start in range(0,len(todo),128):
            batch=list(pool.map(evaluate,todo[start:start+128]));received=[r for r in batch if r is not None]
            with archive.open('a') as f:
                for r in received:rows[r['case_id']]=r;f.write(json.dumps(r,separators=(',',':'))+'\n')
            status='provider_error' if any(r['initial']['status']=='provider_error' for r in received) else 'budget_limited' if len(received)<len(batch) else 'running'
            report(status);print(json.dumps({'processed':len(rows),'planned':5504,'budget':budget.totals(),'status':status}),flush=True)
            if status!='running':return
    report('complete')
    with archive.open('rb') as a,gzip.open(directory/'responses.jsonl.gz','wb',compresslevel=9) as b:b.write(a.read())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--register',action='store_true');p.add_argument('--directory',type=Path,default=Path(os.getenv('DATABASE_PATH','data/riskgraph.sqlite3')).parent/'travel-scale');a=p.parse_args()
    if a.register:write(ROOT/'docs/examples/travel-scale-preregistration.json',registration());print('Scale design frozen; no paid requests')
    else:run(a.directory)
