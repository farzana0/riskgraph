"""Operator-only bounded live jobs; public output contains synthetic records only."""
import json,os
from pathlib import Path
from threading import Lock
from uuid import uuid4
from .travel import generate
from .providers import MODELS
from .travel_calls import TravelBudget
from scripts.travel_study import execute
from scripts.hard_benchmark import write

LOCK=Lock()


def directory():
    p=Path(os.getenv('DATABASE_PATH','data/riskgraph.sqlite3')).parent/'travel-v1';p.mkdir(parents=True,exist_ok=True);return p


def start(family,model,seed):
    if not LOCK.acquire(blocking=False):raise ValueError('A live booking evaluation is already running')
    try:
        d=directory();study=d/'study.json'
        if not study.exists() or json.loads(study.read_text())['status']=='running':raise ValueError('The registered travel study must finish before live requests')
        if TravelBudget(d/'requests.sqlite3',1.2,256).totals()['accounted_estimated_usd']>=1.2:raise ValueError('The shared travel credit allowance is exhausted')
        case=next(c for c in generate(seed,1) if c['family']==family);jid=uuid4().hex
        path=d/('live-'+jid+'.json');write(path,{'id':jid,'status':'running','case':case,'model':model});write(d/'latest-live.json',{'id':jid})
        return jid
    except BaseException:LOCK.release();raise


def run(jid):
    d=directory();p=d/('live-'+jid+'.json');j=json.loads(p.read_text())
    try:
        def progress(row):write(p,{**j,**row})
        row=execute(d,j['case'],j['model'],'travel-live:'+jid,progress)
        write(p,{**j,**row,'status':'complete','budget':TravelBudget(d/'requests.sqlite3',1.2,256).totals()})
    except Exception as exc:write(p,{**j,'status':'unavailable','error_type':type(exc).__name__,'message':'No booking was executed. Inspect provider status or the shared credit allowance.'})
    finally:LOCK.release()


def read(jid=None):
    d=directory()
    if jid is None:
        latest=d/'latest-live.json'
        if not latest.exists():return {'available':False}
        jid=json.loads(latest.read_text())['id']
    if len(jid)!=32 or any(c not in '0123456789abcdef' for c in jid):raise ValueError('Unknown live run')
    p=d/('live-'+jid+'.json')
    return {'available':True,'job':json.loads(p.read_text())} if p.exists() else {'available':False}
