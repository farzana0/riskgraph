"""Offline verification and figure for the frozen factorial experiment. No API calls."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.hardcases import generate_hard, digest
from app.hardbench import MODELS, outcome, summarize, PRICES


def analyze(path):
    study=json.loads(path.read_text())
    assert study['phase']=='heldout' and study['status']=='complete'
    cases=generate_hard(study['design'].get('heldout_seed',2102137),study['design'].get('heldout_repeats',4))
    assert study['cases']==cases
    assert digest(cases)==study['design']['phases']['heldout']['sha256']
    assert digest(study['memory'])==study['design']['retrieved_memory_sha256']
    assert len(study['cells'])==len(cases)*4
    index={c['id']:c for c in cases};seen=set();requests=set();cost=0;failures=[]
    families={}
    for cell in study['cells']:
        identity=(cell['case_id'],cell['model'],cell['memory'])
        assert identity not in seen;seen.add(identity)
        assert cell['model'] in MODELS
        case=index[cell['case_id']]
        for stage in ('initial','corrected'):
            call=cell[stage]
            assert cell[stage+'_outcome']==outcome(case,call)
            result=cell[stage+'_outcome']
            assert result['residual_loss_cents'] in (None,0)
            if call.get('request_sha256'):
                assert call['request_sha256'] not in requests;requests.add(call['request_sha256'])
                cost+=call['estimated_cost_usd']
            if call['status']=='complete':
                usage=call['usage'];price=PRICES[call['model']]
                assert abs(call['estimated_cost_usd']-(usage['input_tokens']*price[0]+usage['output_tokens']*price[1])/1e6)<1e-10
            name=cell['model']+':memory='+str(cell['memory'])+':critic='+str(stage=='corrected')
            row=families.setdefault(case['family'],{}).setdefault(name,{'episodes':0,'task_errors':0,'harmful':0,'proposed_loss_cents':0,'unresolved':0})
            row['episodes']+=1;row['task_errors']+=result['task_failure']
            row['unresolved']+=not result['resolved']
            if result['resolved']:
                row['harmful']+=result['proposed_loss_cents']>0;row['proposed_loss_cents']+=result['proposed_loss_cents']
            if result['task_failure']:
                failures.append({'case_id':case['id'],'family':case['family'],'configuration':name,'outcome':result,'proposal':call.get('proposal'),'status':call['status']})
    recalculated=summarize(cases,study['cells'])
    def equivalent(a,b):
        if isinstance(a,float) and isinstance(b,(float,int)):
            return math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-10)
        if type(a) is not type(b):return False
        if isinstance(a,dict):return a.keys()==b.keys() and all(equivalent(a[k],b[k]) for k in a)
        if isinstance(a,list):return len(a)==len(b) and all(equivalent(x,y) for x,y in zip(a,b))
        return a==b
    assert equivalent(recalculated,study['analysis'])
    return {'schema_version':'hard-factorial-verification-v1','verified_case_count':len(cases),'verified_cells':len(seen),
            'verified_stage_outcomes':len(seen)*2,'model_requests':len(requests),'heldout_estimated_cost_usd':cost,
            'study_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'families':families,'failures':failures,
            'source_sha256':{p:hashlib.sha256((Path(__file__).resolve().parents[1]/p).read_bytes()).hexdigest() for p in ['scripts/analyze_hard.py']},
            'floating_tolerance':{'relative':1e-10,'absolute':1e-10},
            'scope':'Recomputed synthetic scoring and analysis; counts exact, floating results compared within stated platform tolerance. No provider calls, model identity certification or production validation'}


def plot(study, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'#f8faf9'})
    arms=study['analysis']['arms']; labels=[('Haiku' if 'haiku' in a['model'] else 'Sonnet')+'\nM'+str(int(a['memory']))+' C'+str(int(a['critic'])) for a in arms]
    colors=['#3e7473' if 'haiku' in a['model'] else '#b47d56' for a in arms]
    fig,axes=plt.subplots(1,3,figsize=(15,5),facecolor='#f8faf9')
    x=np.arange(len(arms))
    axes[0].bar(x,[a['task_failures'] for a in arms],color=colors)
    axes[0].set_title('Task errors, including service failures',loc='left',weight='bold');axes[0].set_ylabel('Episodes out of %d'%len(study['cases']))
    axes[1].bar(x,[a['proposed_loss_usd'] for a in arms],color=colors)
    axes[1].set_title('Unauthorized proposed loss',loc='left',weight='bold');axes[1].set_ylabel('Total USD across tested cases')
    for ax in axes[:2]:
        ax.set_xticks(x,labels,fontsize=8);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    for a in (arms[0],arms[1],arms[4],arms[5]):
        points=[p for p in a['learning_curve'] if p['episodes']]
        if a['completed_episodes'] and not any(p['episodes']==a['completed_episodes'] for p in points):
            points.append({'episodes':a['completed_episodes'],'posterior_mean_usd':a['proposed']['expected_loss_usd']})
        axes[2].plot([p['episodes'] for p in points],[p['posterior_mean_usd'] for p in points],marker='o',label=('Haiku' if 'haiku' in a['model'] else 'Sonnet')+(' + critic' if a['critic'] else ''))
    axes[2].set_title('RiskGraph posterior mean · memory off',loc='left',weight='bold');axes[2].set_xlabel('Completed episodes');axes[2].set_ylabel('Binned proposed loss, USD / episode');axes[2].legend(frameon=False,fontsize=8);axes[2].grid(alpha=.15)
    fig.suptitle('RiskGraph · %d hard cases · %s output tokens'%(len(study['cases']),study['design']['settings']['max_tokens']),x=.05,ha='left',fontsize=18,weight='bold')
    fig.text(.05,.025,'M: memory. C: corrective critic. Synthetic workload; real model outputs. Error counts are empirical. Posterior means are prior-sensitive; credible/confidence intervals are in the report.',fontsize=8,color='#4e6260')
    fig.tight_layout(rect=[.02,.09,.99,.9]);fig.savefig(output,dpi=180);plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('study',type=Path);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--figure',type=Path)
    args=parser.parse_args();result=analyze(args.study);args.output.write_text(json.dumps(result,indent=2)+'\n')
    if args.figure:plot(json.loads(args.study.read_text()),args.figure)
    print(json.dumps({k:result[k] for k in ['verified_case_count','verified_cells','verified_stage_outcomes','model_requests','heldout_estimated_cost_usd']}))
