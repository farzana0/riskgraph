"""Archive a hosted paired campaign and analyze episode-level uncertainty.

Generation evidence is preserved unchanged. Analysis has separate fingerprints.
"""
import hashlib
import json
from pathlib import Path
import sys
import httpx
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.risk import estimate, conditional_mean_sequence
from app.domain import CAP
from app.protocol import verify_handoffs
from app.review import verify_review

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/examples'
BASE='https://riskgraph-fa98.onrender.com'


def analyze(report, snapshots):
    cells=report['cells']
    if report.get('status')!='complete' or any(c['status']!='complete' for c in cells):
        raise ValueError('Campaign is not complete')
    model_rows=[];pairs=[]
    for model in report['models']:
        events=[e for c in cells if c['model']==model for e in snapshots[c['run_id']]['events']]
        if not all(verify_review(e) and verify_handoffs(e) for e in events):raise ValueError('Evidence verification failed')
        g=[e['gross_loss_cents'] for e in events];r=[e['residual_loss_cents'] for e in events]
        # Four model/stream intervals share 5%, unlike per-run UI intervals.
        streams={}
        for name,values in [('proposed',g),('residual',r)]:
            risk=estimate(values,delta=.0125)
            streams[name]={'observed_loss_usd':sum(values)/100,'harmful_episodes':sum(x>0 for x in values),
                           'posterior_mean_usd':risk['expected_loss_usd'],'credible_ci95_usd':risk['expected_loss_ci95'],
                           'prior_sensitivity_usd':risk['prior_sensitivity_usd'],
                           'conditional_mean_sequence':conditional_mean_sequence(values,delta=.0125)}
        model_rows.append({'model':model,'episodes':len(events),'streams':streams,
                           'scenario_types':len({e['case']['category'] for e in events}),
                           'usage':{k:sum(e['usage'].get(k,0) for e in events) for k in ('input_tokens','output_tokens')},
                           'verified_reviews_and_handoffs':len(events)})
    for seed in report['seeds']:
        a,b=[next(c for c in cells if c['seed']==seed and c['model']==m) for m in report['models']]
        left,right=snapshots[a['run_id']]['events'],snapshots[b['run_id']]['events']
        if len(left)!=len(right):raise ValueError('Incomplete pair')
        for x,y in zip(left,right):
            if x['case']!=y['case']:raise ValueError('Unmatched cases')
            pairs.append(x['gross_loss_cents']-y['gross_loss_cents'])
    # D in [-C,C] is mapped to a bounded nonnegative outcome. Its CS targets
    # the running average conditional paired difference, permitting adaptation.
    transformed=[(d+CAP)/2 for d in pairs]
    interval=conditional_mean_sequence(transformed,delta=.05)
    difference={'paired_episodes':len(pairs),'observed_mean_difference_usd':sum(pairs)/len(pairs)/100,
                'conditional_difference_interval_usd':[2*interval['lower_usd']-CAP/100,2*interval['upper_usd']-CAP/100],
                'confidence':.95,'target':'Average conditional Haiku-minus-Sonnet proposed-loss difference over matched episodes; not a future superiority guarantee',
                'separate_error_family':True,'bootstrap_degenerate':len(set(pairs))<=1,
                'bootstrap_note':'A zero-width empirical bootstrap after identical zero losses cannot rule out unseen loss differences; use the bounded uncertainty interval and scope limits'}
    return {'schema_version':'paired-risk-analysis-v1','run_ids':[c['run_id'] for c in cells],
            'models':model_rows,'difference':difference,
            'family':'Four model/stream conditional-mean intervals share 5% error; the paired-difference interval is a separate 5% family',
            'scope':'Synthetic randomized catalogue; posterior means describe binned loss under the stated prior, not production risk or a premium',
            'interpretation':'No observed difference is not evidence of equivalence; these tasks may be too easy to discriminate model behavior',
            'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['app/risk.py','scripts/analyze_paired.py']}}


if __name__=='__main__':
    OUT.mkdir(exist_ok=True)
    with httpx.Client(timeout=60) as client:
        response=client.get(BASE+'/api/model-comparison');response.raise_for_status();report=response.json()['study']
        if report.get('status')!='complete':raise SystemExit('Campaign is still running; no incomplete analysis saved')
        snapshots={}
        for cell in report['cells']:
            r=client.get(BASE+'/api/runs/'+cell['run_id']+'/export');r.raise_for_status()
            snapshot=r.json();snapshots[cell['run_id']]=snapshot
            (OUT/f"paired-{cell['model']}-{cell['seed']}.json").write_text(json.dumps(snapshot,indent=2)+'\n')
    original=json.dumps(report,indent=2)+'\n'
    (OUT/'paired-models.json').write_text(original)
    analysis=analyze(report,snapshots)
    analysis['campaign_sha256']=hashlib.sha256(original.encode()).hexdigest()
    (OUT/'paired-model-analysis.json').write_text(json.dumps(analysis,indent=2)+'\n')
    print(json.dumps(analysis,indent=2))
