"""Synthetic settlement-layer outcome models, separate from the refund runtime.

These are financial outcome simulations, not injections into a real payment API.
Incomplete settlement episodes are retained and are never labeled zero loss.
"""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.assessment import AssessmentRequest, assess
from app.risk import conditional_mean_sequence

ROOT=Path(__file__).resolve().parents[1]
NAMES=['payment_replay','wrong_recipient','concurrent_balance_race','stale_policy_gate','fail_open_timeout',
       'partial_write_recovery','poisoned_shared_memory','critic_false_assurance','critic_false_alarm',
       'common_dependency_compromise','delegation_loop','delayed_settlement']


def run(seed=20261023,episodes=1000):
    rng=np.random.default_rng(seed);rows=[];examples=[]
    for name in NAMES:
        outcomes=[];gmeans=[];rmeans=[];service=0;pending=0;previous=False
        for i in range(episodes):
            g=r=0;gm=rm=0.
            if name in ('delegation_loop','delayed_settlement'):
                pending+=1
                continue
            if name=='payment_replay':rm=.03*2500;r=2500 if rng.random()<.03 else 0
            elif name=='wrong_recipient':rm=.02*7500;r=7500 if rng.random()<.02 else 0
            elif name=='concurrent_balance_race':rm=.05*10000;r=10000 if rng.random()<.05 else 0
            elif name=='partial_write_recovery':rm=.01*2500;r=2500 if rng.random()<.01 else 0
            elif name=='stale_policy_gate':
                gm,rm=.2*2500,.1*2500;g=2500 if rng.random()<.2 else 0;r=g if rng.random()<.5 else 0
            elif name=='fail_open_timeout':
                gm,rm=.05*100000,.005*100000;g=100000 if rng.random()<.05 else 0;r=g if rng.random()<.1 else 0
            elif name=='poisoned_shared_memory':gm=.3*7500;g=7500 if rng.random()<.3 else 0
            elif name=='critic_false_assurance':gm=.1*100000;g=100000 if rng.random()<.1 else 0
            elif name=='critic_false_alarm':service+=int(rng.random()<.25)
            elif name=='common_dependency_compromise':
                p=.7 if previous else .01
                gm,rm=p*2500,p*100000
                previous=rng.random()<p
                g,r=(2500,100000) if previous else (0,0)
            outcomes.append({'proposed_loss_cents':g,'residual_loss_cents':r});gmeans.append(gm);rmeans.append(rm)
            if name=='payment_replay':examples.append({'episode_id':f'replay-{i}','terminal':True,'adjudicated':True,'proposed_loss_cents':g,'residual_loss_cents':r})
        if pending:
            rows.append({'scenario':name,'episodes':episodes,'completed':0,'unresolved':pending,
                         'assessment':'unavailable_missing_outcomes','observed_loss_usd':None,
                         'interpretation':'Loop/settlement status is observable; financial outcome is unresolved and cannot be scored zero'})
            continue
        result=assess(AssessmentRequest(exposure_cap_cents=100000,sampling='adaptive',outcomes=outcomes))
        row={'scenario':name,'episodes':episodes,'completed':episodes,'unresolved':0,
             'proposed_loss_usd':result['proposed']['observed_loss_usd'],'residual_loss_usd':result['residual']['observed_loss_usd'],
             'execution_loss_increases':result['execution_loss_increases'],'service_abstentions':service,
             'posterior_mean_usd':{k:result[k]['expected_loss_usd'] for k in ('proposed','residual')},
             'family_bounds':{}}
        for stream,field,means in [('proposed','proposed_loss_cents',gmeans),('residual','residual_loss_cents',rmeans)]:
            bound=conditional_mean_sequence([o[field] for o in outcomes],delta=.05/20)
            target=sum(means)/len(means)/100
            row['family_bounds'][stream]={**bound,'known_simulation_target_usd':target,'target_in_interval':bound['lower_usd']<=target<=bound['upper_usd']}
        rows.append(row)
    path=ROOT/'docs/examples/execution-fault-episodes.json'
    path.write_text(json.dumps(examples,indent=2)+'\n')
    return {'schema_version':'operational-outcomes-v1','seed':seed,'episodes_per_scenario':episodes,
            'scenarios':rows,'completed_episodes':sum(r['completed'] for r in rows),'unresolved_episodes':sum(r['unresolved'] for r in rows),
            'provider_requests':0,'simulation_type':'Specified numeric financial outcome models, not real runtime or payment-API fault injection',
            'scope':'Ten completed-scenario stream pairs use a shared 5% time-uniform error budget (0.25% per stream); unresolved scenarios have no loss estimate',
            'limitations':['Service and availability are separate from unauthorized-payment loss.',
                           'A critic accepting a harmful proposal does not bypass the deterministic gate in the reference runtime.',
                           'Replay, recipient, race and compromise scenarios model external execution systems; they are not observed defects in RiskGraph.',
                           'Known conditional mean targets are properties of these specified simulation models, not production estimates.'],
            'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['app/assessment.py','app/risk.py','scripts/operational_study.py']}}


if __name__=='__main__':
    result=run();(ROOT/'docs/examples/operational-outcomes.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{k:r.get(k) for k in ('scenario','completed','unresolved','proposed_loss_usd','residual_loss_usd','execution_loss_increases')} for r in result['scenarios']],indent=2))
