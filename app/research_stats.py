"""Stratified frequency/severity and matched intervention analysis for real calls."""
import numpy as np
from scipy.stats import beta
from .domain import CAP
from .providers import MODELS
from .research_cases import FAMILIES
from .risk import SEVERITY_CENTS, conditional_mean_sequence

SETUPS = {'agent':(False,False),'critic':(False,True),'memory':(True,False),'both':(True,True)}
DRAWS = 12000


def interval(k,n,alpha):
    if not n:return [0.,1.]
    return [float(beta.ppf(alpha,k,n-k+1)) if k else 0.,float(beta.ppf(1-alpha,k+1,n-k)) if k<n else 1.]


def analyze(study):
    families=FAMILIES;weight=1/len(families);nplan=len(study['cases']);arms={};records={}
    final=study['status']=='complete'
    for model in MODELS:
        for setup,(memory,critic) in SETUPS.items():
            key=model+':'+setup;stage='corrected' if critic else 'initial'
            selected=[c for c in study['cells'] if c['model']==model and c['memory']==memory]
            records[key]={c['case_id']:c[stage+'_outcome'] for c in selected}
            frequency=np.zeros(DRAWS);loss_samples=np.zeros(DRAWS);mean=loss_mean=0.;upper=0.;cells={}
            for si,family in enumerate(families):
                rows=[c[stage+'_outcome'] for c in selected if c['family']==family]
                complete=[r for r in rows if r['resolved']]
                positive=[r['proposed_loss_cents'] for r in complete if r['proposed_loss_cents']>0]
                n,k=len(complete),len(positive);aa,bb=k+.5,n-k+.5
                counts=np.zeros(4)
                for value in positive:counts[np.searchsorted(SEVERITY_CENTS,value)]+=1
                rng=np.random.default_rng(np.random.SeedSequence([2026102405,si]))
                p=rng.beta(aa,bb,DRAWS);q=rng.dirichlet(counts+.25,DRAWS)@SEVERITY_CENTS/100
                frequency+=weight*p;loss_samples+=weight*p*q
                posterior=aa/(aa+bb);severity=float((counts+.25)@SEVERITY_CENTS/(k+1)/100)
                mean+=weight*posterior;loss_mean+=weight*posterior*severity
                cp=interval(k,n,.05/(8*len(families)))
                upper+=weight*cp[1]
                cells[family]={'n':n,'k':k,'unresolved':len(rows)-n,'planned':nplan//len(families),
                    'posterior_mean':posterior,'posterior_a':aa,'posterior_b':bb,'credible95':beta.ppf([.025,.975],aa,bb).tolist(),
                    'severity_counts':counts.astype(int).tolist(),'severity_mean_usd':severity,'mean_binned_loss_usd':posterior*severity,
                    'exact_upper':cp[1] if final and n==nplan//len(families) else None}
            complete=[r for r in records[key].values() if r['resolved']];losses=[r['proposed_loss_cents'] for r in complete]
            residual=[r['residual_loss_cents'] for r in complete];resolved=len(complete)
            arms[key]={'model':model,'setup':setup,'memory':memory,'critic':critic,'scheduled':nplan,'processed':len(selected),'resolved':resolved,'unresolved':len(selected)-resolved,
                'task_errors':sum(r['task_failure'] for r in records[key].values()),'harmful':sum(v>0 for v in losses),
                'frequency_mean':mean,'frequency_credible95':np.quantile(frequency,[.025,.975]).tolist(),
                'exact_upper':upper if final and resolved==nplan else None,
                'empirical_frequency':sum(v>0 for v in losses)/resolved if resolved else None,
                'observed_loss_usd':sum(losses)/100,'observed_mean_usd':sum(losses)/resolved/100 if resolved else None,
                'residual_loss_usd':sum(residual)/100,'residual_conditional_bound':conditional_mean_sequence(residual,delta=.05/16),
                'binned_loss_mean_usd':loss_mean,'binned_loss_credible95':np.quantile(loss_samples,[.025,.975]).tolist(),
                'conditional_loss_bound':conditional_mean_sequence(losses,delta=.05/16),'cells':cells,
                'missing_outcome_mean_range_usd':[sum(losses)/len(selected)/100,(sum(losses)+(len(selected)-resolved)*CAP)/len(selected)/100] if selected else None}
    comparisons=[]
    def contrast(kind,before,after):
        cell_stats={};sample=np.zeros(DRAWS);mean=lo=hi=0.;avoided=introduced=0;dollars=[];resolved=0
        for si,family in enumerate(families):
            pairs=[]
            for case in study['cases']:
                if case['family']!=family:continue
                a,b=records[before].get(case['id']),records[after].get(case['id'])
                if a and b and a['resolved'] and b['resolved']:pairs.append((a,b))
            counts=[0,0,0,0]
            for a,b in pairs:
                x,y=a['proposed_loss_cents']>0,b['proposed_loss_cents']>0
                counts[0 if x and y else 1 if x else 2 if y else 3]+=1
                dollars.append(a['proposed_loss_cents']-b['proposed_loss_cents'])
            n=len(pairs);avoided+=counts[1];introduced+=counts[2];resolved+=n
            # Marginal Jeffreys Beta(.5,.5) priors; sample each pair jointly.
            params=np.array(counts)+.25;total=params.sum()
            rng=np.random.default_rng(np.random.SeedSequence([2026102407,si]))
            draws=rng.dirichlet(params,DRAWS);sample+=weight*(draws[:,1]-draws[:,2]);mean+=weight*(params[1]-params[2])/total
            one=interval(counts[1],n,.05/(12*len(families)*4));two=interval(counts[2],n,.05/(12*len(families)*4))
            lo+=weight*(one[0]-two[1]);hi+=weight*(one[1]-two[0])
            cell_stats[family]={'n':n,'both_harmful':counts[0],'avoided':counts[1],'introduced':counts[2],'neither_harmful':counts[3]}
        shifts=conditional_mean_sequence([d+CAP for d in dollars],cap=2*CAP,delta=.05/12)
        all_pairs=[(records[before][c['id']],records[after][c['id']]) for c in study['cases'] if c['id'] in records[before] and c['id'] in records[after]]
        comparisons.append({'kind':kind,'before':before,'after':after,'resolved_pairs':resolved,'scheduled_pairs':nplan,
            'avoided':avoided,'introduced':introduced,'task_errors_fixed':sum(a['task_failure'] and not b['task_failure'] for a,b in all_pairs),
            'task_errors_introduced':sum(not a['task_failure'] and b['task_failure'] for a,b in all_pairs),
            'observed_frequency_reduction':(avoided-introduced)/resolved if resolved else None,
            'posterior_frequency_reduction':mean,'credible95':np.quantile(sample,[.025,.975]).tolist(),
            'confidence95':[lo,hi] if final and resolved==nplan else None,
            'observed_loss_reduction_usd':sum(dollars)/resolved/100 if resolved else None,
            'conditional_loss_reduction_bound_usd':[shifts['lower_usd']-CAP/100,shifts['upper_usd']-CAP/100],
            'cells':cell_stats})
    for model in MODELS:
        for a,b in [('agent','critic'),('memory','both')]:contrast('critic',model+':'+a,model+':'+b)
        for a,b in [('agent','memory'),('critic','both')]:contrast('memory',model+':'+a,model+':'+b)
    for setup in SETUPS:contrast('model',MODELS[0]+':'+setup,MODELS[1]+':'+setup)
    return {'arms':arms,'comparisons':comparisons,'families':list(families),'weight_per_family':weight,'posterior_draws':DRAWS,
        'prior':'Independent Jeffreys Beta(.5,.5) frequencies per family/configuration; Dirichlet(.25,.25,.25,.25) over positive-loss severity bands. Paired binary contrasts use a joint four-outcome Dirichlet(.25,.25,.25,.25) prior per family.',
        'severity_band_upper_usd':(SEVERITY_CENTS/100).tolist(),
        'scope':'Equal-weight balanced challenge distribution; synthetic identities/money and real model outputs. Proposed unauthorized loss is separate from executed loss after the fixed gate. No production incidence or universal benefit claim.',
        'uncertainty':'Bayesian intervals are marginal, conditional on the model/priors and equal family weights. Frequency upper bounds have a 5% family over 96 cells; paired frequency contrasts a separate 5% family over 144 scenario/comparison contrasts (576 endpoints). Each requires completed fixed batches and IID case pairs within a family with fixed policies. Conditional monetary confidence sequences allow adaptation: 16 arm/stream intervals share another 5% budget, 12 paired contrasts another 5%. These four families together are not a joint 95% guarantee (union bound at least 80%). Missing outcomes stay unresolved and are excluded, never scored zero.',
        'memory_interpretation':'This tests the total effect of supplying a fixed SurrealDB-retrieved procedural bank, including extra context and stochastic responses. It does not isolate a database-specific causal effect; no context-length or alternative-database control was run.'}
