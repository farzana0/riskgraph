"""Prespecified two-strategy follow-up; no old observations are pooled."""
import numpy as np
from scipy.stats import beta
from .domain import CAP
from .providers import MODELS
from .followup_cases import FAMILIES
from .research_stats import interval
from .risk import SEVERITY_CENTS,conditional_mean_sequence

MODES=('none','selected')
LABELS={'none':'No memory','raw':'Raw memory','selected':'Selected memory','grounded':'Memory + calculations'}
DRAWS=12000


def key(model,mode,critic):return model+'|'+mode+'|'+str(int(critic))


def contrasts():
    result=[]
    for model in MODELS:
        for critic in (False,True):
            for kind,a,b in [('memory','none','selected')]:
                result.append((kind,key(model,a,critic),key(model,b,critic)))
        for mode in MODES:result.append(('critic',key(model,mode,False),key(model,mode,True)))
    for mode in MODES:
        for critic in (False,True):result.append(('model',key(MODELS[0],mode,critic),key(MODELS[1],mode,critic)))
    return result


def analyze(study):
    weight=1/len(FAMILIES);nplan=len(study['cases']);arms={};records={};final=study['status']=='complete'
    for model in MODELS:
        for mode in MODES:
            selected=[c for c in study['cells'] if c['model']==model and c['memory_mode']==mode]
            for critic in (False,True):
                armkey=key(model,mode,critic);stage='corrected' if critic else 'initial'
                records[armkey]={c['case_id']:c[stage+'_outcome'] for c in selected}
                pdraw=np.zeros(DRAWS);ldraw=np.zeros(DRAWS);mean=lmean=upper=0.;cells={};sens={}
                for si,family in enumerate(FAMILIES):
                    rows=[c[stage+'_outcome'] for c in selected if c['family']==family];complete=[r for r in rows if r['resolved']]
                    values=[r['proposed_loss_cents'] for r in complete];positive=[v for v in values if v>0];n,k=len(values),len(positive);a,b=k+.5,n-k+.5
                    counts=np.zeros(4)
                    for v in positive:counts[np.searchsorted(SEVERITY_CENTS,v)]+=1
                    rng=np.random.default_rng(np.random.SeedSequence([2026102423,si]));pd=rng.beta(a,b,DRAWS);qd=rng.dirichlet(counts+.25,DRAWS)@SEVERITY_CENTS/100
                    pdraw+=weight*pd;ldraw+=weight*pd*qd;p=a/(a+b);q=float((counts+.25)@SEVERITY_CENTS/(k+1)/100);mean+=weight*p;lmean+=weight*p*q
                    cp=interval(k,n,.05/(8*len(FAMILIES)));upper+=weight*cp[1]
                    cells[family]={'n':n,'k':k,'planned':nplan//len(FAMILIES),'posterior_a':a,'posterior_b':b,'posterior_mean':p,'credible95':beta.ppf([.025,.975],a,b).tolist(),'severity_counts':counts.astype(int).tolist(),'mean_binned_loss_usd':p*q,'unresolved':len(rows)-n}
                    for fp in (.5,1.):
                        for sp in (.5,1.,2.):
                            label='frequency_'+str(fp)+'_severity_'+str(sp);concentration=counts+sp/4
                            sens[label]=sens.get(label,0.)+weight*(k+fp)/(n+2*fp)*float(concentration@SEVERITY_CENTS/concentration.sum()/100)
                rows=list(records[armkey].values());completed=[r for r in rows if r['resolved']];losses=[r['proposed_loss_cents'] for r in completed];residual=[r['residual_loss_cents'] for r in completed];n=len(completed)
                arms[armkey]={'model':model,'memory_mode':mode,'critic':critic,'scheduled':nplan,'processed':len(rows),'resolved':n,'unresolved':len(rows)-n,
                    'harmful':sum(v>0 for v in losses),'task_errors':sum(r['task_failure'] for r in rows),'empirical_frequency':sum(v>0 for v in losses)/n if n else None,
                    'frequency_mean':mean,'frequency_credible95':np.quantile(pdraw,[.025,.975]).tolist(),'exact_upper':upper if final and n==nplan else None,
                    'observed_loss_usd':sum(losses)/100,'observed_mean_usd':sum(losses)/n/100 if n else None,'residual_loss_usd':sum(residual)/100,
                    'binned_loss_mean_usd':lmean,'binned_loss_credible95':np.quantile(ldraw,[.025,.975]).tolist(),'prior_sensitivity_usd':[min(sens.values()),max(sens.values())],
                    'conditional_loss_bound':conditional_mean_sequence(losses,delta=.05/16),'residual_conditional_bound':conditional_mean_sequence(residual,delta=.05/16),
                    'missing_outcome_mean_range_usd':[sum(losses)/len(rows)/100,(sum(losses)+(len(rows)-n)*CAP)/len(rows)/100] if rows else None,'cells':cells}
    comparisons=[];definitions=contrasts()
    for kind,before,after in definitions:
        samples=np.zeros(DRAWS);mean=lo=hi=0.;cell_counts={};avoided=introduced=resolved=0;pairs=[]
        for case in study['cases']:
            a,b=records[before].get(case['id']),records[after].get(case['id'])
            if a and b:pairs.append((case,a,b))
        for si,family in enumerate(FAMILIES):
            rows=[(a,b) for c,a,b in pairs if c['family']==family and a['resolved'] and b['resolved']];counts=[0,0,0,0]
            for a,b in rows:
                x,y=a['proposed_loss_cents']>0,b['proposed_loss_cents']>0;counts[0 if x and y else 1 if x else 2 if y else 3]+=1
            n=len(rows);avoided+=counts[1];introduced+=counts[2];resolved+=n;params=np.array(counts)+.25
            rng=np.random.default_rng(np.random.SeedSequence([2026102427,si]));q=rng.dirichlet(params,DRAWS);samples+=weight*(q[:,1]-q[:,2]);mean+=weight*(params[1]-params[2])/params.sum()
            alpha=.05/(len(definitions)*len(FAMILIES)*4);one=interval(counts[1],n,alpha);two=interval(counts[2],n,alpha);lo+=weight*(one[0]-two[1]);hi+=weight*(one[1]-two[0])
            cell_counts[family]={'n':n,'both_harmful':counts[0],'avoided':counts[1],'introduced':counts[2],'neither_harmful':counts[3]}
        dollars=[a['proposed_loss_cents']-b['proposed_loss_cents'] for c,a,b in pairs if a['resolved'] and b['resolved']]
        cs=conditional_mean_sequence([v+CAP for v in dollars],cap=2*CAP,delta=.05/len(definitions))
        comparisons.append({'kind':kind,'before':before,'after':after,'scheduled_pairs':nplan,'resolved_pairs':resolved,'avoided':avoided,'introduced':introduced,
            'task_errors_fixed':sum(a['task_failure'] and not b['task_failure'] for c,a,b in pairs),'task_errors_introduced':sum(not a['task_failure'] and b['task_failure'] for c,a,b in pairs),
            'observed_frequency_reduction':(avoided-introduced)/resolved if resolved else None,'posterior_frequency_reduction':mean,'credible95':np.quantile(samples,[.025,.975]).tolist(),
            'confidence95':[lo,hi] if final and resolved==nplan else None,'observed_loss_reduction_usd':sum(dollars)/len(dollars)/100 if dollars else None,
            'conditional_loss_reduction_bound_usd':[cs['lower_usd']-CAP/100,cs['upper_usd']-CAP/100],'cells':cell_counts})
    return {'arms':arms,'comparisons':comparisons,'families':list(FAMILIES),'modes':list(MODES),'mode_labels':LABELS,'weight_per_family':weight,'posterior_draws':DRAWS,
        'prior':'Independent family/configuration Jeffreys Beta(.5,.5) frequencies and Dirichlet(.25,.25,.25,.25) severity bands. Matched contrasts use joint four-outcome Dirichlet(.25,.25,.25,.25) priors, preserving Beta margins.',
        'scope':'Three equally weighted regression-enriched hard families; fresh seed, unchanged generator complexity. Old results are development evidence only and are not pooled. No production traffic claim.',
        'uncertainty':'Marginal Bayesian intervals depend on the stated priors/model and equal family weights. Frequency exact upper bounds allocate 5% over 24 cells. Paired frequency contrast intervals allocate a separate 5% over 36 family/comparison contrasts (144 one-sided endpoints). They require a complete fixed batch, fixed policies and IID pairs within family. Two additional separate 5% families cover 16 arm/stream conditional-dollar sequences and 12 paired-dollar sequences. Together these four frequentist families are not a joint 95% guarantee (union bound at least 80%). Missing responses remain unresolved, excluded from financial estimates and counted as task errors.',
        'memory_interpretation':'Selected memory versus none changes recalled procedural context and the usage contract jointly. Both use the same current records and base policy. No record-calculation report is supplied in this follow-up. A Sonnet critic is a separate request under the same memory condition. Context length, instructions and added critic compute are not independently controlled.'}


def precision(study):
    """Prespecified balanced prefixes; marginal Bayesian summaries, not extra trials."""
    n=study['design']['per_family'];points=[]
    for count in sorted(set([k for k in (4,8,12,16,24,32,48,64,100) if k<=n]+[n])):
        ids=set()
        for family in FAMILIES:
            ids.update(c['id'] for c in [x for x in study['cases'] if x['family']==family][:count])
        subset={**study,'cases':[c for c in study['cases'] if c['id'] in ids], 'cells':[c for c in study['cells'] if c['case_id'] in ids], 'status':'prefix'}
        a=analyze(subset)
        points.append({'per_family':count,'cases':len(ids),'comparisons':[c for c in a['comparisons'] if c['kind'] in ('memory','critic','model')]})
    return points
