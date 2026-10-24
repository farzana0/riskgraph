"""Operator-only bounded live jobs; public output contains synthetic records only."""
import json,os,random
from .hardcases import digest
from pathlib import Path
from threading import Lock
from uuid import uuid4
from .travel import generate
from .providers import MODELS
from .live_budget import LiveBudget as TravelBudget
from scripts.hard_benchmark import write

LOCK=Lock()


def directory():
    p=Path(os.getenv('DATABASE_PATH','data/riskgraph.sqlite3')).parent/'travel-v1';p.mkdir(parents=True,exist_ok=True);return p


def live_case(family,seed):
    """Counterbalance candidate identities for new discretionary live requests."""
    c=next(c for c in generate(seed,1) if c['family']==family)
    rng=random.Random(seed^2026102499)
    ids={q['offer_id']:'offer-'+('%016x'%rng.getrandbits(64)) for q in c['observation']['quotes']}
    flights={q['flight_id']:'flight-'+('%016x'%rng.getrandbits(64)) for q in c['observation']['quotes']}
    for q in c['observation']['quotes']:q['offer_id']=ids[q['offer_id']];q['flight_id']=flights[q['flight_id']]
    for b in c['observation']['booking_ledger']:
        if b['flight_id'] in flights:b['flight_id']=flights[b['flight_id']]
    c['truth']['valid_offer_id']=ids[c['truth']['valid_offer_id']];c['truth']['trap_offer_id']=ids[c['truth']['trap_offer_id']]
    c['id']='live-'+digest([family,seed])[:16]
    return c


def start(family,model,seed):
    if not LOCK.acquire(blocking=False):raise ValueError('A live booking evaluation is already running')
    try:
        d=directory();study=d/'study.json'
        if not study.exists() or json.loads(study.read_text())['status']=='running':raise ValueError('The registered travel study must finish before live requests')
        if TravelBudget(d/'requests.sqlite3',1.2,256).totals()['accounted_estimated_usd']>=1.2:raise ValueError('The shared travel credit allowance is exhausted')
        case=live_case(family,seed);jid=uuid4().hex
        path=d/('live-'+jid+'.json');write(path,{'id':jid,'status':'running','case':case,'model':model});write(d/'latest-live.json',{'id':jid})
        return jid
    except BaseException:LOCK.release();raise


def run(jid):
    from .travel_calls import call
    from .providers import Agent
    from .travel import outcome
    d=directory();p=d/('live-'+jid+'.json');j=json.loads(p.read_text());row={}
    budget=None
    try:
        budget=TravelBudget(d/'requests.sqlite3',1.2,256)
        agent=Agent();key='travel-live:'+jid
        initial=call(agent,budget,j['case']['observation'],j['model'],key+':initial')
        row={'case_id':j['case']['id'],'family':j['case']['family'],'model':j['model'],'initial':initial,'initial_outcome':outcome(j['case'],initial)}
        if initial['status']=='complete':write(p,{**j,**row,'status':'reviewing'})
        corrected=call(agent,budget,j['case']['observation'],MODELS[1],key+':critic',initial['proposal']) if initial['status']=='complete' else {'status':'not_started','code':'initial_proposal_unavailable'}
        row.update(corrected=corrected,corrected_outcome=outcome(j['case'],corrected))
        write(p,{**j,**row,'status':'complete','budget':budget.totals()})
    except Exception as exc:write(p,{**j,**row,'status':'unavailable','error_type':type(exc).__name__,'message':'No booking was executed. Inspect provider status or the shared credit allowance.'})
    finally:
        if budget is not None:budget.db.close()
        LOCK.release()


def read(jid=None):
    d=directory()
    if jid is None:
        latest=d/'latest-live.json'
        if not latest.exists():return {'available':False}
        jid=json.loads(latest.read_text())['id']
    if len(jid)!=32 or any(c not in '0123456789abcdef' for c in jid):raise ValueError('Unknown live run')
    p=d/('live-'+jid+'.json')
    return {'available':True,'job':json.loads(p.read_text())} if p.exists() else {'available':False}


def start_review(case_id):
    """Review one saved scale proposal; excluded from all registered estimates."""
    if not LOCK.acquire(blocking=False):raise ValueError('A live evaluation is already running')
    try:
        d=directory();candidates=[d.parent/'travel-scale/study.json',Path(__file__).resolve().parents[1]/'docs/examples/travel-scale.json']
        source=next((p for p in candidates if p.is_file()),None)
        if source is None:raise ValueError('The scale evidence is preparing')
        evidence=json.loads(source.read_text());case=next((c for c in evidence['cases'] if c['id']==case_id),None);row=next((r for r in evidence['cells'] if r['case_id']==case_id),None)
        if not case or not row or row['initial']['status']!='complete':raise ValueError('Choose a saved usable proposal')
        jid=uuid4().hex;j={'id':jid,'status':'reviewing','kind':'review_saved','case':case,'model':MODELS[0],'initial':row['initial'],'initial_outcome':row['initial_outcome'],'scope':'Discretionary review of an illustrative saved failure; excluded from registered risk estimates.'}
        write(d/('live-'+jid+'.json'),j);write(d/'latest-live.json',{'id':jid});return jid
    except BaseException:LOCK.release();raise


def run_review(jid):
    from .travel_calls import call
    from .providers import Agent
    from .travel import outcome
    d=directory();p=d/('live-'+jid+'.json');j=json.loads(p.read_text())
    try:
        budget=TravelBudget(d/'requests.sqlite3',1.2,256)
        corrected=call(Agent(),budget,j['case']['observation'],MODELS[1],'travel-live-review:'+jid+':critic',j['initial']['proposal'])
        write(p,{**j,'corrected':corrected,'corrected_outcome':outcome(j['case'],corrected),'status':'complete','budget':budget.totals()})
    except Exception as exc:write(p,{**j,'status':'unavailable','error_type':type(exc).__name__,'message':'No booking was executed. The shared live allowance or provider status prevented completion.'})
    finally:LOCK.release()
