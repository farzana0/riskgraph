"""Server-side, budgeted paired model evaluation; never prints credentials.

Run inside the deployed service so provider keys remain in its environment.
Resume skips completed model/seed cells; partial cells are not retried implicitly.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import numpy as np
from scipy.stats import binomtest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.engine import Engine
from app.store import Store
from app.providers import MODELS, ProviderError
from app.domain import generate
from app.protocol import verify_handoffs

ROOT=Path(__file__).resolve().parents[1]
PRICES={'claude-haiku-5-5':(.10,.50),'claude-sonnet-5-5':(2.,10.)}


def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data,indent=2)+'\n')
    temporary.replace(path)


def summarize(engine, cells, seeds):
    summary=[]
    for model in MODELS:
        selected=[c for c in cells if c['model']==model and c['status']=='complete']
        summary.append({'model':model,'episodes':sum(c['episodes'] for c in selected),
                        'harmful_proposals':sum(c['harmful_proposals'] for c in selected),
                        'proposed_loss_usd':sum(c['proposed_loss_usd'] for c in selected),
                        'residual_loss_usd':sum(c['residual_loss_usd'] for c in selected),
                        'unpaid_eligible':sum(c['unpaid_eligible'] for c in selected),
                        'estimated_cost_usd':sum(c['estimated_cost_usd'] for c in selected)})
    pairs=[]
    for seed in seeds:
        a=next((c for c in cells if c['seed']==seed and c['model']==MODELS[0] and c['status']=='complete'),None)
        b=next((c for c in cells if c['seed']==seed and c['model']==MODELS[1] and c['status']=='complete'),None)
        if a and b:
            ae,be=engine.store.events(a['run_id']),engine.store.events(b['run_id'])
            for x,y in zip(ae,be):
                if x['case']!=y['case']:raise ValueError('Paired cases differ')
                pairs.append((x['gross_loss_cents'],y['gross_loss_cents']))
    comparison={'paired_episodes':len(pairs),'target':'Haiku minus Sonnet proposed loss on the same synthetic cases; neither model is assumed worse'}
    if pairs:
        values=np.asarray(pairs)/100
        differences=values[:,0]-values[:,1]
        # Descriptive paired bootstrap; no sequential or production guarantee.
        rng=np.random.default_rng(20261021)
        means=np.mean(rng.choice(differences,size=(10000,len(differences)),replace=True),axis=1)
        discordant=[int(np.sum((values[:,0]>0)&(values[:,1]==0))),int(np.sum((values[:,1]>0)&(values[:,0]==0)))]
        comparison.update(mean_difference_usd=float(differences.mean()),bootstrap_ci95_usd=np.quantile(means,[.025,.975]).tolist(),
                          discordant_harm_counts=discordant,
                          exact_mcnemar_p=float(binomtest(discordant[0],sum(discordant),.5).pvalue) if sum(discordant) else 1.,
                          interpretation='Descriptive paired bootstrap and exact discordance test; shared seeded cases, no production or superiority claim from zero discordances')
    return summary,comparison


def run(args):
    db=Path(os.getenv('DATABASE_PATH','data/riskgraph.sqlite3'))
    path=args.output or db.parent/'model-comparison.json'
    engine=Engine(Store(str(db)))
    if not os.getenv('ANTHROPIC_API_KEY'):raise SystemExit('Provider is not configured')
    cells=[]
    if path.exists():
        saved=json.loads(path.read_text())
        if saved.get('seeds')!=args.seeds or saved.get('cases_per_cell')!=args.cases:
            raise SystemExit('Existing comparison has a different design; choose a new output file')
        cells=saved['cells']
    report={'schema_version':'paired-model-v1','seeds':args.seeds,'cases_per_cell':args.cases,
            'suite':'random_stress','memory':False,'critic':False,'cells':cells,
            'models':list(MODELS),'prompt_version':'refund-proposer-v2',
            'settings':{'max_tokens':700,'effort':'low','haiku_thinking':'disabled','sonnet_thinking':'between_tools'},
            'price_basis_usd_per_million':PRICES,'max_estimated_spend_usd':args.max_usd,
            'limitations':['Different models and supported reasoning settings are compared together.',
                            'The uniform synthetic scenario mixture does not estimate a production incidence rate.',
                            'Temperature is not set; case generation is reproducible, model responses need not be.',
                            'Generated order IDs are episode-local. No live payment system is called.',
                            'Bootstrap intervals are descriptive; no adaptive sample-size superiority claim.'],
            'case_hashes':{str(s):hashlib.sha256(json.dumps([c.model_dump() for c in generate(s,args.cases,'random_stress')],sort_keys=True).encode()).hexdigest() for s in args.seeds}}
    for seed in args.seeds:
        # Alternate ordering by seed to reduce systematic time/order confounding.
        models=MODELS if seed%2 else tuple(reversed(MODELS))
        for model in models:
            existing=next((c for c in cells if c['seed']==seed and c['model']==model),None)
            if existing:
                if existing['status']!='complete':raise SystemExit('Partial cell retained; inspect provider and persisted events before explicit resumption')
                continue
            if len(engine.store.runs())>=30:raise SystemExit('Workspace run limit reached')
            cost=sum(c.get('estimated_cost_usd',0) for c in cells)
            if cost+.10>args.max_usd:raise SystemExit('Estimated spend margin reached')
            run=engine.create(seed,args.cases,'claude',False,'random_stress',model=model)
            cell={'seed':seed,'model':model,'run_id':run['id'],'status':'running','episodes':0,'estimated_cost_usd':0}
            cells.append(cell);write(path,report)
            for i in range(args.cases):
                if sum(c.get('estimated_cost_usd',0) for c in cells)+.10>args.max_usd:
                    write(path,report);raise SystemExit('Estimated spend margin reached; no automatic retry')
                try:
                    snapshot=engine.step(run['id'],i)
                except ProviderError as exc:
                    cell['status']='provider_error';cell['error']=exc.diagnostic
                    write(path,report);print(json.dumps({'model':model,'seed':seed,'status':'provider_error','detail':exc.diagnostic}),flush=True)
                    return
                if not verify_handoffs(snapshot['events'][-1]):raise RuntimeError('Handoff receipt mismatch')
                tokens=snapshot['tokens'];p=PRICES[model]
                cell.update(episodes=i+1,estimated_cost_usd=(tokens['input_tokens']*p[0]+tokens['output_tokens']*p[1])/1e6)
                write(path,report)
                time.sleep(.3)
            cell.update(status='complete',harmful_proposals=snapshot['gross']['failures'],
                        proposed_loss_usd=snapshot['gross']['observed_loss_usd'],residual_loss_usd=snapshot['residual']['observed_loss_usd'],
                        unpaid_eligible=snapshot['unnecessary_abstentions'],tokens=snapshot['tokens'],
                        categories=snapshot['scenario_summary'],reviews_verified=snapshot['quality']['reviews_verified'])
            report['summary'],report['paired_comparison']=summarize(engine,cells,args.seeds)
            report['status']='complete' if len(cells)==len(args.seeds)*len(MODELS) and all(c['status']=='complete' for c in cells) else 'running'
            write(path,report);print(json.dumps(cell),flush=True)
    report['source_sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['app/providers.py','app/engine.py','app/scenarios.py','scripts/compare_models.py']}
    write(path,report)
    print(json.dumps({'status':report['status'],'summary':report['summary'],'comparison':report['paired_comparison']}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--seeds',type=int,nargs='+',default=[2102111,2102112,2102113,2102114])
    parser.add_argument('--cases',type=int,default=40,choices=range(1,41))
    parser.add_argument('--max-usd',type=float,default=5.)
    parser.add_argument('--output',type=Path)
    run(parser.parse_args())
