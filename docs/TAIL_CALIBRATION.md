# Tail uncertainty calibration audit

The [offline audit](examples/tail-calibration.json) runs 40,000 independent binary datasets across five sample sizes and four fixed event probabilities, with eight equally weighted scenario families. It reproduces the existing Jeffreys family-frequency posterior and conservative exact upper bound. It makes no provider requests and does not tune the registered model after observing outcomes.

The distinction between credible intervals and confidence bounds is material. At four observations per family and true event probabilities of 0.1% or 1%, the model-based central 95% credible interval covers the fixed truth in none of the 2,000 simulated datasets per regime. The independent family priors contribute substantial aggregate pseudo-events. At 688 per family and true probability 0.1%, coverage is 73.9%; at true probability 5%, it is 94.4%. These are Monte Carlo diagnostics, not mathematical guarantees or provider error rates.

The conservative weighted exact upper endpoint covers the fixed truth in all simulated datasets in these regimes. This is consistent with its intentionally conservative construction; the confidence guarantee comes from the binomial construction and union bound under the stated assumptions, not from finite simulation success. The audit does not establish exact 95% calibration under arbitrary dependence, shifting policies or an unknown production mix.

The website therefore keeps posterior estimates, marginal credible intervals, exact upper bounds, conditional-dollar sequences, unresolved outcomes and missing-dollar sensitivity distinct. The large campaign additionally reports a fully observed harmful-or-unresolved endpoint. Its upper bound does not impute a financial loss to missing proposals. No prior or analysis is changed in response to this audit; a different pooling model would require a new prospective protocol.

Reproduce with `python scripts/tail_calibration.py`. The random seed, dataset counts and posterior simulation budget are recorded in the script and report.
