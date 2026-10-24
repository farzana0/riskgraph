"""Known-truth estimator calibration, separate from agent performance and saved cases."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from scipy.stats import beta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.paired_demo import WEIGHTS, SCENARIOS
from app.paired_diagnostics import PAIRED_ENDPOINT_ALPHA

# Statistical test distributions, not the refund agent's measured probabilities.
P=np.array([[.02,.01,.03,.005],[.75,.02,.20,.01],[.70,.01,.25,.005],
            [.65,.015,.30,.01],[.80,.02,.35,.01],[.80,.025,.40,.015]])


def bounds(k,n,alpha):
    lower=np.where(k==0,0,beta.ppf(alpha,np.maximum(k,1),n-k+1))
    upper=np.where(k==n,1,beta.ppf(1-alpha,k+1,np.maximum(n-k,1)))
    return lower,upper


def coverage(value):
    successes=int(np.sum(value)); n=len(value)
    low=0 if successes==0 else float(beta.ppf(.025,successes,n-successes+1))
    high=1 if successes==n else float(beta.ppf(.975,successes+1,n-successes))
    return {'fraction':successes/n,'successes':successes,'repetitions':n,'monte_carlo_exact95':[low,high]}


def run(repetitions=2000,seed=20261024,posterior_draws=1000):
    weights=np.array([WEIGHTS[s] for s in SCENARIOS]); results=[]
    for n in (10,60):
        for correlation in (0.,.8,1.):
            # One independently seeded simulated dataset per repetition.
            counts=[]; avoided=[];introduced=[]
            for repetition in range(repetitions):
                rng=np.random.default_rng(np.random.SeedSequence([seed,n,int(correlation*100),repetition]))
                shared=rng.random((6,n,1)); separate=rng.random((6,n,4))
                coupled=rng.random((6,n,1))<correlation
                values=np.where(coupled,shared,separate)<P[:,None,:]
                counts.append(values.sum(axis=1))
                avoided.append((values[:,:,0,None]&~values[:,:,1:]).sum(axis=1))
                introduced.append((~values[:,:,0,None]&values[:,:,1:]).sum(axis=1))
            k=np.array(counts); av=np.array(avoided); intro=np.array(introduced)
            cp=bounds(k,n,.05/24)[1]
            hoeffding=np.minimum(1,k/n+np.sqrt(np.log(24/.05)/(2*n)))
            pair_low=bounds(av,n,PAIRED_ENDPOINT_ALPHA)[0]-bounds(intro,n,PAIRED_ENDPOINT_ALPHA)[1]
            pair_high=bounds(av,n,PAIRED_ENDPOINT_ALPHA)[1]-bounds(intro,n,PAIRED_ENDPOINT_ALPHA)[0]
            truth_delta=P[:,0,None]-P[:,1:]
            cp_project=np.einsum('s,rsc->rc',weights,cp)
            hoeffding_project=np.einsum('s,rsc->rc',weights,hoeffding)
            known_projection=weights@P
            # Repeated-sampling diagnostic of the DEFAULT joint Bayesian
            # projection; fewer MC draws than the production 12,000 are disclosed.
            truth_weighted_delta=weights@truth_delta
            joint_covered=[];joint_width=[]
            for repetition in range(repetitions):
                rng=np.random.default_rng(np.random.SeedSequence([seed,n,int(correlation*100),repetition,999]))
                a10=.5+av[repetition];a01=.5+intro[repetition]
                concordant=1+n-av[repetition]-intro[repetition]
                discordance=rng.beta((a10+a01)[...,None],concordant[...,None],size=(6,3,posterior_draws))
                direction=rng.beta(a10[...,None],a01[...,None],size=(6,3,posterior_draws))
                delta=np.einsum('s,scd->cd',weights,discordance*(2*direction-1))
                lower,upper=np.quantile(delta,[.025,.975],axis=1)
                joint_covered.append((lower<=truth_weighted_delta)&(truth_weighted_delta<=upper))
                joint_width.append(upper-lower)
            joint_covered=np.array(joint_covered)
            prior_coverage={}
            for a,b in ((.5,.5),(1.,1.),(2.,2.)):
                lo=beta.ppf(.025,a+k,b+n-k);hi=beta.ppf(.975,a+k,b+n-k)
                cover=((lo<=P)&(P<=hi)).mean(axis=0)
                prior_coverage['Beta(%g,%g)'%(a,b)]={'cellwise_coverage':cover.tolist(),'range_across_24_cells':[float(cover.min()),float(cover.max())]}
            results.append({'cases_per_scenario':n,'total_paired_cases':6*n,'shared_latent_fraction':correlation,
                'exact_frequency_family_coverage':coverage((cp>=P).all(axis=(1,2))),
                'hoeffding_frequency_family_coverage':coverage((hoeffding>=P).all(axis=(1,2))),
                'paired_difference_family_coverage':coverage(((pair_low<=truth_delta)&(truth_delta<=pair_high)).all(axis=(1,2))),
                'exact_projected_upper_mean':cp_project.mean(axis=0).tolist(),
                'hoeffding_projected_upper_mean':hoeffding_project.mean(axis=0).tolist(),
                'true_projected_probabilities':known_projection.tolist(),
                'joint_bayesian_reduction_sampling_coverage':[coverage(joint_covered[:,i]) for i in range(3)],
                'joint_bayesian_reduction_mean_interval_width':np.mean(joint_width,axis=0).tolist(),
                'credible_interval_cellwise_sampling_coverage':prior_coverage})
    return {'version':'known-truth-calibration-v1','seed':seed,'repetitions_per_setting':repetitions,
        'joint_projection_draws_per_dataset':posterior_draws,'production_joint_draws':12000,'independent_datasets':6*repetitions,'probabilities':P.tolist(),'scenario_order':list(SCENARIOS),
        'configuration_order':['synthetic_A','synthetic_B','synthetic_C','synthetic_D'],
        'weights':WEIGHTS,'results':results,
        'scope':'Estimator calibration under explicitly specified Bernoulli distributions. These configurations are statistical test labels, not measured agent/rule performance. Not pooled with the frozen refund dataset.',
        'comparison':'Exact Clopper-Pearson and Hoeffding use identical cases, counts, 24-cell simultaneous target and error budget. Two sample sizes are reported separately. No claim of improved sample efficiency.',
        'interpretation':'Coverage fractions have Monte Carlo uncertainty. Bayesian credible-interval coverage is reported descriptively per cell, not asserted to be 95%. The paired-difference 95% family and frequency 95% family are separate guarantees, not a joint 95% guarantee.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--repetitions',type=int,default=2000);parser.add_argument('--seed',type=int,default=20261024);parser.add_argument('--posterior-draws',type=int,default=1000);parser.add_argument('--output',default='docs/examples/paired-model-calibration.json');args=parser.parse_args()
    if args.repetitions<100:parser.error('Use at least 100 independent repetitions per setting')
    
    if args.posterior_draws<200:parser.error('Use at least 200 posterior draws')
    report=run(args.repetitions,args.seed,args.posterior_draws);path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2)+'\n')
    print('Saved',report['independent_datasets'],'known-truth datasets to',path)
    for r in report['results']:
        print('n=%s, coupled=%s: CP %.4f, Hoeffding %.4f, paired %.4f'%(r['cases_per_scenario'],r['shared_latent_fraction'],r['exact_frequency_family_coverage']['fraction'],r['hoeffding_frequency_family_coverage']['fraction'],r['paired_difference_family_coverage']['fraction']))
