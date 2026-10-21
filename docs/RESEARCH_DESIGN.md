# RiskGraph: episode-level assurance for tool-using agent workflows

## Research question and claim boundary

Can a system separate unsafe agent proposals from executed financial loss, quantify uncertainty with few adjudicated episodes, and monitor financial severity while agents adapt?

The implemented contribution is an integrated, reproducible reference system: a typed workflow, independent policy gate, auditable outcome scoring, paired model evaluation, frequency/severity estimation and sequential monitoring. The statistical constructions apply published methods. This release does not claim a new concentration theorem, formal verification of the Python runtime, an insurance pricing model, or a demonstrated production error rate.

## Research foundations

| Published work | Venue | Use in RiskGraph | What has not been established |
|---|---|---|---|
| [Why Do Multi-Agent LLM Systems Fail?](https://proceedings.neurips.cc/paper_files/paper/2025/hash/b1041e52d3be19f0a9bc491657488e4a-Abstract-Datasets_and_Benchmarks_Track.html), Cemri et al. | NeurIPS 2025, Datasets and Benchmarks | Organizes failure analysis around system design, inter-agent alignment and verification | The local scenarios are not a reproduction of MAST-Data, and no full MAST coverage score is claimed |
| [AgentDojo](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html), Debenedetti et al. | NeurIPS 2024, Datasets and Benchmarks | Motivates executable task checks and untrusted tool/content boundaries | AgentDojo tasks and attack set have not been run here |
| [InjecAgent](https://aclanthology.org/2024.findings-acl.624/), Zhan et al. | Findings of ACL 2024 | Motivates indirect instructions, forged authority and data-source attacks | No published InjecAgent score is claimed; exfiltration is not monetized by this refund loss model |
| [Time-uniform, nonparametric, nonasymptotic confidence sequences](https://doi.org/10.1214/20-AOS1991), Howard et al. | Annals of Statistics 49(2), 2021 | Mixture-supermartingale confidence sequences and repeated-observation validity | Mathematical guarantees require the stated filtration, bounded outcomes and precommitted parameters |
| [Estimating means of bounded random variables by betting](https://doi.org/10.1093/jrsssb/qkad009), Waudby-Smith and Ramdas | JRSS Series B 86(1), 2024 | Foundation for bounded-outcome betting and sequential inference | The implementation uses a specified mixture; it does not implement every variance-adaptive construction in the paper |

Conference papers guide the agent evaluation design; leading statistics journals supply the inference foundations. Product documentation is implementation evidence, not peer-reviewed evidence of safety.

## System and authority

```
Trusted case + policy ───────────────────────────────────────────┐
Untrusted customer text → proposer model → optional critic model │
Untrusted incident recall ──────────────→ advisory context        │
                                    ↓                          ↓
                     deterministic policy reviewer → execution gate
                                                        ↓
                                      transactional synthetic ledger
                                                        ↓
                                  scored episode + incident provenance
```

| Role | Input and output | Authority and failure behavior |
|---|---|---|
| Memory retriever | Up to three incident records with source IDs | Read context only; recall failures are recorded and do not change policy |
| Proposer | Trusted case, untrusted text/context → strict refund/decline/escalate proposal | No payment, policy-edit, shell or arbitrary tool capability; one bounded request |
| Optional critic | Same case and proposed action → accept/review advice | Separate Sonnet call; cannot authorize, rewrite or execute a payment; shared model errors may remain correlated |
| Policy reviewer | Structured proposal and trusted order facts → explicit checks and digest | Deterministic read-only implementation; disagreement with the gate stops the case |
| Execution gate | Trusted order state and structured proposal → allow/block | Sole logical payment authority; ownership, order, date, amount, balance and approval limits |
| Ledger | Allowed synthetic action → committed event and ledger entry | Atomic transaction and per-run order replay protection |
| Risk assessor | Adjudicated episode outcomes → estimates, bounds and alarms | No execution authority; missing outcomes are not zeros |

Handoff receipts bind run ID, sequence, case, proposal, critique, policy review, gate result and executed amount through a fixed directed sequence. Verification recomputes the chain and monetary accounting. Receipts are hashes, not signatures: an attacker controlling all facts and recomputing all receipts is outside this consistency check. Provider errors and malformed output cause no case execution; requests remain counted even if they fail. The runtime has no delegation loop or automatic paid retry. Process isolation and a wall-clock workflow watchdog are not implemented.

## Gate soundness within the synthetic policy

For a schema-valid refund, an allowed gate verdict implies: the order ID matches, the authenticated customer owns the order, its age is at most 30 days, and the positive proposed amount is at most the requested amount, remaining paid balance, and 20,000 cents. Therefore it is at most the scoring oracle’s authorized amount and `score(case, proposal)=0`. Non-refund actions execute no payment and score zero. This is an algebraic argument about the specified predicates. Randomized differential tests check the implementation against that argument; they do not prove the process, trusted inputs or external payment service correct.

## Loss and sampling unit

One business episode may contain many agents and messages. Let G_t be unauthorized loss if its proposed payment were executed, and R_t be unauthorized executed loss after controls. In this synthetic world, the policy oracle defines authorization from trusted facts. Wrong order/owner or an expired refund makes the whole proposed amount unauthorized; otherwise only the excess above authorized money is counted. Service refusals are tracked separately.

The synthetic bound is 0 ≤ R_t ≤ G_t ≤ C, with C=$1,000. Imported assessments require their own cap fixed before observing the data, reviewed numeric outcomes and one terminal record per episode. Proposed loss is a defined counterfactual exposure, not a claim that each dollar would become an insured claim. Do not sum losses from repeated agent descriptions of the same payment. A batch with several distinct payments needs a separately adjudicated episode loss and a cap covering its aggregate exposure.

No independence between agents within an episode is assumed. In particular, system failure probability is not computed by multiplying agent success probabilities. Shared context, common model families, coordinated attacks and common tool failures can correlate their errors.

## Statistical framework

### Frequency and positive severity

A Beta(1/2,1/2) prior models the frequency of positive loss. A Dirichlet(1/4,1/4,1/4,1/4) prior models positive severity rounded upward to C×(0.025,0.10,0.50,1). Posterior mean binned loss is posterior frequency × posterior positive severity; 16,000 deterministic draws give a 95% credible interval. Alternative prior strengths expose sensitivity.

This is a model-based description, especially in designed or adaptive stress tests. It is not a calibrated frequentist interval, predictive portfolio loss interval, premium, VaR or expected shortfall. Zero failures leaves nonzero posterior risk; it does not empirically identify an unseen tail. Import normalization rounds upward in integer arithmetic, with at most C/100000 extra cents before severity binning.

### Adaptive conditional-mean confidence sequence

Let F_(t-1) contain the complete history before episode t, X_t=L_t/C ∈ [0,1], and m_t=E[X_t | F_(t-1)]. The target at n is the running average of conditional means, not a fixed future-workload parameter:

    theta_n = C/n × sum_(t=1)^n m_t.

Hoeffding's lemma gives exp(lambda S_n − lambda² n/8) a nonnegative supermartingale, where S_n=sum(X_t−m_t). Mix lambda with N(0,1/rho), using the prespecified rho=6.25. The resulting process is

    M_n = sqrt(rho/(rho+n/4)) × exp(S_n²/[2(rho+n/4)]).

Ville's inequality and inversion yield radius

    w_n = sqrt((rho+n/4) × log((rho+n/4)/(rho delta²))) / n.

The interval is C×[max(0,mean(X)−w_n), min(1,mean(X)+w_n)]. It permits adaptive dependence and changing conditional means. Each before/after stream receives delta=.025; a union bound gives at least 95% simultaneous coverage over both streams and all n within an assessment. Different n target different theta_n, so intervals are not intersected over time. Complete outcome reporting, a cap chosen in advance and a coherent episode sequence remain essential.

The older beta-mixture loss-tail bound remains available only under fixed conditional tail probabilities. It can be tighter for a stable workload. It is disabled for memory adaptation, designed catalogues, drift and correlated suites. Neither construction licenses forecasting an arbitrary new deployment distribution.

### Financial severity and frequency alarms

The existing harm-frequency alarm tests P(G_t>0 | F_(t-1)) ≤ 0.10. A new monetary alarm tests E[G_t | F_(t-1)] ≤ $10, with C=$1,000. For normalized reference b=.01 and each precommitted lambda in (2.5,5,10,20,30,50), factors 1+lambda(X_t−b) are nonnegative and have conditional expectation at most one under the null. Fixed mixtures over bets and start times preserve the supermartingale property; unstarted capital stays at one.

An e-value of 20 triggers each alarm with at most 5% probability ever under its own conditional null. The alarms have separate budgets: when both nulls hold, the union is bounded by 10%, not 5%. Loss-bound coverage is a separate family. Restart times and weights are fixed before data; there are no post-hoc free resets. An alert is evidence against a reference, not a proof of a specific change point. No alert does not establish safety.

## Reproducible experiments

1. **Gate conformance.** Random structured proposals, deliberately faulty agents, memory fault doubles, malformed provider outputs, replay/tampering checks. These measure agreement with the specified policy, not a model's real-world failure probability.
2. **Paired model benchmark.** Haiku 5.5 and Sonnet 5.5 receive identical generated cases from four fixed seeds, 40 cases per seed, the same prompt/schema and memory off. Ordering alternates by seed. Supported reasoning configurations differ and are recorded: Haiku disabled thinking, Sonnet between-tools thinking; both use low effort and 700 max tokens. No larger-model superiority is assumed. Compare proposed loss, harmful proposals, residual loss, service abstentions, usage and matched discordance. Paired bootstrap intervals are descriptive, not sequential superiority guarantees. Zero discordance is not equivalence.
3. **Optional critic smoke evaluation.** Proposer and critic calls are both budgeted and recorded. A successful demonstration validates the call/handoff path; causal risk improvement requires a matched ablation with faulty proposals and is not claimed here.
4. **Sequential simulations.** Fixed-horizon paired paths cover rare catastrophes, severity changes, adaptive feedback and common-cause bursts. Compare detection and null crossing; check the conditional-mean target using known simulated conditional expectations. Monte Carlo intervals accompany rates. These are simulation checks of implementation, not replacements for the derivation.

Raw results: [assurance study](examples/assurance-study.json), [existing failure campaign](examples/failure-campaign.json), [historical framework comparison](examples/framework-v2.json). Live paired results, when recorded, are available at `/api/model-comparison` and through the Stress tests page. The campaign runner caps estimated spending with a margin and shares the persistent workspace request budget. Provider billing remains the actual spend authority.

## Threat and evidence gaps

| Failure family | Implemented checks | Remaining research work |
|---|---|---|
| Policy/identity/amount errors | Trusted-state gate, two deterministic predicates, 28 local scenario categories | Real policy exceptions and authenticated external state |
| Prompt and peer manipulation | Untrusted-context separation, forged authority, poisoned-memory test doubles, advisory critic cannot grant authority | Benchmark transfer and adaptive attacker optimization |
| Handoff disagreement/replay | Case-bound receipts, stage-order verification, atomic ledger uniqueness | Distributed delivery, signed principals and recovery across services |
| Shared failures | Adaptive CS, clustered and common-cause simulations; episode aggregation | Independent real-world workloads and multi-provider common-cause measurement |
| Missing outcomes | Intake rejects incomplete/duplicate final episode records | Delayed claims, censoring, audit sampling and under-reporting models |
| Heavy-tail severity | Explicit cap, separate monetary alarm, rare-catastrophe simulations | Unbounded loss tails, aggregate portfolios and cap violations |
| Data exposure/resource exhaustion | Fixed task/tool scope, bounded calls, provider timeouts, request budget | Privacy scoring, sandbox escapes, process compromise, workflow deadlines and production load testing |

## Technical presentation

A defensible demonstration shows: an unsafe proposed payment and its policy explanation; observed loss separated from uncertain mean risk; identical cases under two models; a rare expensive failure missed by frequency monitoring but sometimes detected by the monetary monitor; and explicit unresolved evidence gaps. The claim is a research-informed assurance prototype with reproducible synthetic evidence. It is not a certified insurer, a proof of general agent safety, or a peer-reviewed new method.
