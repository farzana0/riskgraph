# Paired risk model and statistical audit

RiskGraph's homepage and `/demo` topology view use saved agent decisions and trusted ledger outcomes. The **Model checks** panel adds a dependency-aware comparison model, prior sensitivity, analytic posterior variance, and conservative fixed-sample bounds. It does not change the frozen 60-case evidence or the existing unpooled Beta–Binomial frequency model.

## Targets and evidence

For scenario s and monitoring setup m, Y=1 means a completed case executed positive unauthorized-payment exposure. A reference/monitor pair uses the same proposal, reviewer verdict, and original ledger snapshot. Only matched, completed outcomes enter a paired comparison; errors and missing outcomes remain unresolved. Their omission can be informative, so partial-cohort Bayesian summaries are conditional descriptions, not automatic extrapolations to the full planned population.

The reference is **No monitor**. Positive Δ means lower unauthorized-payment probability with monitoring. Monetary exposure reduction is the separately weighted observed difference in integer-cent outcomes, not a probability or measured business loss. Service changes count legitimate completions among eligible matched requests.

The main model remains p[s,m] ~ Beta(a,b), posterior Beta(a+k,b+n−k), default a=b=1. With independent scenario priors, weighted posterior mean and variance have closed forms:

    μ = Σ w[s] A[s] / (A[s]+B[s])
    Var = Σ w[s]² A[s]B[s] / [(A[s]+B[s])²(A[s]+B[s]+1)]

A=A_prior+k, B=B_prior+n−k. The app computes the mean and variance analytically; 12,000 reproducible posterior draws approximate the equal-tailed credible interval. It does not substitute a normal approximation. Weights are an illustrative assumed traffic mix, not frequencies estimated from the balanced challenge set.

## Dependency-aware paired Bayesian model

For each scenario and reference/monitor comparison, let q11, q10, q01, q00 be the probabilities of the paired binary outcomes. Category 10 is harmful without monitoring and harmless with monitoring; category 01 is an introduced harmful outcome. The counts are an observed 2×2 table, not two independent binomial samples.

The pair model uses a Dirichlet–multinomial likelihood/prior:

    (q11,q10,q01,q00) ~ Dirichlet(a²/T, ab/T, ab/T, b²/T), T=a+b
    posterior parameters = prior parameters + matched category counts

This is an explicit modeling choice. Aggregating the first and second cells gives a Beta(a,b) prior for reference risk; aggregating the first and third gives the same prior for monitored risk. At a=b=1 the joint prior is Dirichlet(0.5,0.5,0.5,0.5). When the matched cohort equals the marginal-analysis cohort, both posterior marginals exactly match the existing Beta–Binomial model. With missing arm outcomes the cohorts can differ; the app reports matched counts and does not silently treat them as the full marginal sample.

The risk contrast is Δ = q10−q01. For posterior discordant parameters A and B and concordant total C, a convenient exact factorization is:

    D ~ Beta(A+B,C), R ~ Beta(A,B), independently
    Δ = D(2R−1)
    E[Δ] = (A−B)/(A+B+C)
    Var[Δ] = [(A+B)/(A+B+C) − E[Δ]²] / (A+B+C+1)

D is discordant probability mass and R its direction. This samples a joint paired posterior, rather than subtracting independent arm-probability samples. Scenario-specific contrasts are weighted using the selected mixture; scenario priors remain independent. The app uses 12,000 reproducible draws per comparison and analytic mean/variance checks. Each displayed contrast interval is a **marginal Bayesian credible interval**, conditional on this joint prior and matched cohort. The three comparisons are not asserted independent, and no simultaneous Bayesian coverage or global ranking probability is supplied.

The implementation is in [paired_diagnostics.py](../app/paired_diagnostics.py). A direct 100,000-draw Dirichlet reference test checks the factorized sampler's mean, variance, and quantiles; complete-cohort tests check agreement with the original Beta marginal means.

## Conservative frequentist paired contrasts

A separate construction bounds the same risk difference without a joint Bayesian prior. In each scenario, n10 and n01 are individually binomial marginal counts of discordant outcomes over n matched cases. Their dependence is retained; the method never assumes they are independent.

For each discordant probability, form exact one-sided Clopper–Pearson lower/upper endpoints. Let their bounds be [L10,U10] and [L01,U01]. Then:

    Δ lies in [L10−U01, U10−L01]

There are six scenarios, three comparisons with No monitor, and four one-sided endpoints per comparison: **72 endpoints**. Assign each endpoint error 0.05/72. The union bound gives at least 95% simultaneous coverage across the 18 scenario/comparison contrasts under IID case pairs within each scenario, fixed policies, and the predetermined sampling plan. Dependence between comparisons is permitted. Nonnegative normalized weights preserve those contrast bounds by weighted summation; the cell-coverage event also supports interactive weight choices within the six specified families.

This interval is conservative and is not a shortest exact multinomial interval. Even ten avoided outcomes and zero introduced outcomes in a single stratum can remain inconclusive under the 72-endpoint budget. Wide intervals are retained, not shortened for presentation. An exhaustive small multinomial enumeration test checks coverage of the construction for dependent paired outcomes.

The contrast bounds appear only after the entire held-out batch is complete and resolved. They are unavailable during replay, for a batch containing errors, and for development, curated examples, or the three designed archived real-model cases. They are **not anytime bounds**.

### Two separate error families

The original 24-cell frequency upper bounds retain their required 0.05/24 allocation. The paired contrast family has its own 0.05/72 allocation. Each family has at least 95% coverage under its assumptions; their conjunction is **not a joint 95% guarantee**. A union bound gives at least 90% for both families together. Bayesian credible intervals are not included in either frequentist guarantee.

## Prior sensitivity

The panel recomputes the same counts under the selected prior, Jeffreys Beta(0.5,0.5), uniform Beta(1,1), and symmetric stronger Beta(2,2), omitting duplicates. This reports sensitivity, not a data-driven choice of the best prior. The range across priors is not an uncertainty interval with a coverage interpretation.

For the unchanged zero-failure rule-enabled cells, the weighted posterior means are 4.55%, 8.33%, and 14.29% under those three reference priors. Counts and the frequentist bound do not change. The model does not turn a narrow policy-kernel proof into a zero-risk prior for an entire deployed system.

## Known-truth calibration study

Run:

```sh
python scripts/calibrate_paired_model.py --repetitions 2000 --posterior-draws 1000
```

The [saved report](examples/paired-model-calibration.json) records 12,000 independently seeded synthetic datasets across two sample sizes (10 or 60 cases per scenario) and three within-case dependence settings. Its four configurations are generic statistical test labels, **not measured agent, Claude, or policy-rule failure probabilities**. All true Bernoulli probabilities, seeds, traffic weights, and sample sizes are disclosed. It is not pooled with the frozen refund evidence.

Clopper–Pearson and Hoeffding upper bounds use identical observations, the same 24-cell simultaneous target, and the same error budget. The study reports family coverage and mean projected upper endpoints at each sample size. No sample-efficiency claim is made. It separately measures repeated-sampling coverage of marginal Bayesian cell intervals and weighted joint Bayesian contrast intervals. Those results are diagnostics, not assertions that Bayesian intervals must have 95% frequentist coverage.

For tractable repeated simulation, the joint-contrast calibration uses 1,000 posterior draws per dataset, versus 12,000 in the application. Monte Carlo coverage intervals are provided; finite posterior-draw quantile error is an additional limitation. The study tests specified stationary synthetic distributions, not arbitrary dependence across requests, production traffic, source authenticity, or real payment settlement.

## Operational graph integration

The topology renderer and explanatory animations were supplied through the Claude design handoff and integrated with the existing backend. The production controller loads `/api/paired-demo` and `/api/paired-demo/analyze` directly. The on-demand audit calls `/api/paired-demo/diagnostics`. Offline snapshot fallback is absent in production; failed requests display an error and clearly label any retained verified results.

The initial workflow draws a saved complete path, while admitted evidence stays at zero. Replays admit stable outcome IDs only on completion. Step seeking never admits an outcome. Configurations change the display, not the evidence. The density morph is a visual transition between calculated curves, not a sequence of newly inferred posteriors. Payload text, captions, ledger changes, and stop markers come from recorded events. Customer text remains untrusted; editable SVG source assets are separate from the live data-driven renderer.

## References and scope

- [Clopper and Pearson, Biometrika (1934)](https://doi.org/10.1093/biomet/26.4.404): exact binomial endpoint construction.
- [SciPy 1.13.1 exact binomial intervals](https://docs.scipy.org/doc/scipy-1.13.1/reference/generated/scipy.stats._result_classes.BinomTestResult.proportion_ci.html): implementation convention and original reference.
- [SciPy Dirichlet distribution](https://docs.scipy.org/doc/scipy-1.13.1/reference/generated/scipy.stats.dirichlet.html): density, positive concentration parameters, and moments.
- [Hoeffding, JASA (1963)](https://doi.org/10.1080/01621459.1963.10500830): bounded-observation comparison bound.

The paired-model composition and its use for this demo are modeling/engineering choices, not a claim of a new published theorem. The system estimates narrowly defined unauthorized-payment frequency under specified scenario distributions. It does not establish production calibration, annual tail loss, CVaR, causality of historical memory experiments, or whole-agent formal safety.
