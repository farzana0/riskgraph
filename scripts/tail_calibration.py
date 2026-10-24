"""Offline uncertainty audit; no model calls and no tuning of registered methods."""
import json
from pathlib import Path
import numpy as np
from scipy.stats import beta


def run():
    rng=np.random.default_rng(2026102497);records=[];replicates=2000;draws=1024
    for n in (4,16,64,256,688):
        for probability in (.001,.01,.05,.2):
            counts=rng.binomial(n,probability,(replicates,8));q=np.zeros((replicates,draws))
            for family in range(8):q+=rng.beta(counts[:,family,None]+.5,n-counts[:,family,None]+.5,(replicates,draws))/8
            lower,upper=np.quantile(q,[.025,.975],axis=1);exact=np.where(counts==n,1,beta.ppf(1-.05/32,counts+1,n-counts)).mean(axis=1)
            records.append({'per_family':n,'cases':8*n,'true_probability':probability,'bayesian_credible_coverage':float(np.mean((lower<=probability)&(probability<=upper))),'bayesian_mean_interval_width':float(np.mean(upper-lower)),'exact_upper_coverage':float(np.mean(probability<=exact)),'replicates':replicates})
    return {'version':'tail-uncertainty-audit-v1','datasets':len(records)*replicates,'posterior_draws_per_dataset':draws,'records':records,'scope':'40,000 independent simulated binary datasets across twenty fixed-probability/sample-size regimes, eight equal-weight families. This is a fixed-truth stress audit of the existing marginal Jeffreys model and conservative CP upper bound; it is not a model error-rate estimate or a proof of Bayesian frequentist calibration. Exact weighted bounds are conservative. Monte Carlo intervals are not used to tune the registered priors.'}

if __name__=='__main__':
    r=run();Path('docs/examples/tail-calibration.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
