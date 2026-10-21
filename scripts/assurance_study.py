"""Paired monetary/frequency alarms and adaptive confidence-sequence stress."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from scipy.special import logsumexp
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.risk import BET_GRID, alarm_starts
from simulate import proportion

ROOT=Path(__file__).resolve().parents[1]


def log_paths(values, reference):
    n,t=values.shape
    bets=BET_GRID*.1/reference
    prefix=np.concatenate([np.zeros((n,1,len(bets))),np.cumsum(np.log1p((values[:,:,None]-reference)*bets),axis=1)],axis=1)
    capital=np.zeros((n,t));used=0
    for start,weight in alarm_starts(t):
        component=np.ones((n,t))
        component[:,start:]=np.exp(logsumexp(prefix[:,start+1:]-prefix[:,start:start+1],axis=2)-np.log(len(bets)))
        capital+=weight*component;used+=weight
    return np.log(capital+1-used)


def run(paths=10000,horizon=500,seed=20261021):
    rng=np.random.default_rng(seed);rows=[]
    t=np.arange(1,horizon+1);rho=6.25;variance=rho+t/4
    width=np.sqrt(variance*np.log(variance/(rho*.025**2)))/t
    designs=['bounded_mean_null','rare_catastrophe_02','severity_shift','adaptive_feedback','common_cause_burst']
    for name in designs:
        frequency_hits=money_hits=cs_misses=0;means=[]
        for start in range(0,paths,200):
            count=min(200,paths-start)
            rates=np.full((count,horizon),.02);severity=np.ones((count,horizon))
            if name=='bounded_mean_null':rates[:]=.01
            if name=='severity_shift':rates[:]=.1;severity[:,:100]=.025
            if name=='common_cause_burst':rates[:]=.005;rates[:,200:225]=.8
            draws=rng.random((count,horizon))
            if name=='adaptive_feedback':
                harm=np.zeros((count,horizon),bool)
                for i in range(horizon):
                    rates[:,i]=np.where(harm[:,i-1],.7,.02) if i else .02
                    harm[:,i]=draws[:,i]<rates[:,i]
            else:harm=draws<rates
            loss=harm*severity
            frequency_hits+=int((log_paths(harm.astype(float),.1)>=np.log(20)).any(axis=1).sum())
            money_hits+=int((log_paths(loss,.01)>=np.log(20)).any(axis=1).sum())
            target=np.cumsum(rates*severity,axis=1)/t
            empirical=np.cumsum(loss,axis=1)/t
            cs_misses+=int((np.abs(empirical-target)>width).any(axis=1).sum())
            means.extend((loss.mean(axis=1)*1000).tolist())
        row={'scenario':name,'trajectories':paths,'horizon':horizon,
             'frequency_alarm':proportion(frequency_hits,paths),'monetary_alarm':proportion(money_hits,paths),
             'adaptive_cs_anytime_miss':proportion(cs_misses,paths),'observed_mean_loss_usd':float(np.mean(means)),
             'money_null_holds':name=='bounded_mean_null'}
        rows.append(row);print(json.dumps(row),flush=True)
    return {'schema_version':'assurance-study-v1','seed':seed,'trajectories':paths*len(designs),'observations':paths*horizon*len(designs),
            'horizon':horizon,'provider_requests':0,'money_reference_usd':10,'frequency_reference':.1,'each_alarm_error':.05,
            'per_stream_cs_error':.025,'rho':rho,'cap_usd':1000,'scenarios':rows,
            'interpretation':['Both alarms use the same simulated losses; differences are paired descriptive results.',
                              'The new CS targets average conditional expected loss, even with adaptive dependence, not future workload risk.',
                              'Each alarm has a separate 5% budget; either-alarm null crossing is bounded by 10% when both nulls hold.',
                              'Monte Carlo supports implementation checks; the guarantee follows from assumptions and the martingale derivation.',
                              'Monetary reference and mixture settings are prespecified; sensitivity is not guaranteed for every alternative.'],
            'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['app/risk.py','scripts/assurance_study.py']}}


if __name__=='__main__':
    path=ROOT/'docs/examples/assurance-study.json';path.write_text(json.dumps(run(),indent=2)+'\n')
