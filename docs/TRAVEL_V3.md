# Record-grounded travel workflow: prospective replication

The previous matched study contains 28 unnecessary escalations and five unsafe booking proposals, all five involving deadline violations. All 256 responses completed normally. Initial Haiku used about 795 output tokens on average, compared with about 392 for Sonnet; neither reached the shared 1,536-token limit. This is not evidence that a generally stronger model is worse. It identifies observable errors on one finite challenge set: incorrect signed time arithmetic, unsupported additional restrictions, and actions inconsistent with their short explanations. Early action commitment in the action-first JSON schema, distraction from long procedural memory, and overly broad review instructions are hypotheses, not established internal causes. The common schema is deliberately unchanged in the replication.

## Fresh matched controls

Thirty-two new trips cross two models, memory off/on, critic off/on, and two workflows: the exact original workflow versus a revised record-grounded workflow. Both workflows see identical fresh trips. Every request uses the unchanged Booking JSON schema, adaptive thinking, low effort and 1,536-token cap. The critic is always a separate Sonnet request. Initial responses are reused for critic-off outcomes, never counted twice as independent observations. Eight families have four trips each, including one no-eligible-offer control per family. Opaque identifiers, shuffled competing revisions, exact zero/one-second deadline boundaries, exact 3,600-second connections, 40–60 fee entries, duplicate/cancelled/sibling-trip ledger distractors, and multiple valid alternatives increase difficulty.

The revised workflow adds read-only, source-indexed arithmetic for every model/memory arm: current revisions, exact fee sums, UTC instants, signed deadline-minus-arrival seconds, elapsed connection seconds and exact trip/flight ledger joins. The packet contains no eligible-offer label, recommended action, gate verdict or hidden scoring state. Both models retain the raw source records. Memory-on supplies compact current, content-verified SurrealDB procedures rather than a long provenance-rich record in the prompt; source facts, temporal validity and retrieval traces remain in the archive. The revised critic receives the saved action/IDs/amount but not its speculative prose, and may change it only for a concrete record-backed reason. No deterministic postprocessor repairs model decisions before scoring. The independent execution gate remains unchanged.

Within each workflow, the memory and critic contrasts measure those interventions on the same trips. Across-workflow contrasts measure the whole revised package, including the arithmetic view and prompting, and must not be attributed solely to memory or to SurrealDB. There is no alternative-database or equal-context-length placebo control.

## Discovery and unknown failures

A separate development stage runs both models on four different trips, then asks each model to enumerate at most six candidate failure modes with cited trace IDs, relevant fields, proposed mutations and qualitative loss mechanisms. Candidates are either trace-supported occurrences or untested hypotheses. The development traces, model suggestions and discovery requests never enter the held-out risk counts. Suggestions cannot execute code or set truth labels, and they are not automatically promoted into the test generator. This demonstrates open-ended enumeration from a few runs without claiming exhaustive coverage or an estimated probability for undiscovered failures.

## Risk and uncertainty

The preregistered eight-family Bayesian frequency/paired models from the original comparison are reused separately for each workflow. Eight additional paired contrasts compare the workflows at identical model/memory/critic settings. Model-based intervals are marginal and prior-sensitive. The primary frequentist audit uses weighted Hoeffding bounds, allowing independent but differently distributed trips and preserving dependence within paired configurations. One simultaneous 95% family covers all 240 frequency, paired-effect and monetary intervals over both workflows. The fixed eligibility quotas do not establish the stronger within-family IID assumption of the retained binomial reference intervals, so those are not the primary conservative bounds. Unknown proposals retain their full $0–$1,000 loss range, and no fixed-batch bounds are shown before completion. Loss remains an assumed synthetic cancellation/nonrefundability or price-discrepancy exposure; no travel reservation or payment API exists.

The held-out experiment has a separate persistent US$7.50 cap and 512-request cap. Discovery has US$0.50 and ten requests. Combined new spending cannot exceed US$8 regardless of account auto-reload. Atomic reservations precede calls. Unknown/error requests retain their conservative reserve and are not automatically retried. Cases, source hashes, bank digests, settings and the older archive hash are frozen before requests; the target is fixed and never extended according to results.

## Source mixing

Reviewed observed episodes, designed simulations and illustrative examples retain distinct provenance. Unreviewed or unresolved labels never become zero loss. Production incidence cannot be inferred by pooling deliberately oversampled stress cases with real traces. A projection must declare the scenario weights, the observed/simulation transfer weight, and an assumed unmodeled-failure mass. An undiscovered component with unknown failure probability remains bounded from zero to one, and its severity by the declared cap. These are sensitivity assumptions, not quantities learned from a few discovery runs.

The original reports remain immutable. New results, discovery provenance, an independent scorer reconstruction and the mistake audit will be archived separately.

## Bound derivation and implementation audit

For one endpoint, let a_i = w_s/n_s be the fixed trip weight in family s, and let X_i range over an interval of width R. Independence is across trips; configurations for the same trip may be dependent. The weighted [Hoeffding inequality](https://www.tandfonline.com/doi/abs/10.1080/01621459.1963.10500830) yields radius

`r = R sqrt( (log(2 M / alpha) / 2) sum_i a_i^2 )`, with M=240 and alpha=0.05.

For a frequency R=1, dollars R=1000, and a paired before-minus-after difference R=2 or 2000. Missing outcomes give an empirical lower/upper range before adding the radius. Clip to the endpoint support. A union bound supplies joint 95% coverage over the prespecified 240 endpoints without assuming independence between endpoints. The target is the weighted mean expectation under this fixed synthetic trip schedule and fixed workflow, not an arbitrary future traffic distribution. No confidence bound is reported until the registered batch completes. With 32 equally weighted trips, the unclipped frequency radius is about 37.85 percentage points and the paired radius 75.70 points; a small sample cannot supply narrow assumption-light guarantees.

The [known-truth calibration](examples/travel-v3-calibration.json) runs 5,000 independent datasets with heterogeneous trip probabilities, strongly dependent configurations, different severities and unresolved financial labels. Joint coverage over all 240 intervals was 99.98% (Monte Carlo 95% interval 99.905%–99.999%); an intentionally invalid zero-width estimate missed in every dataset. This checks the implementation under these simulated distributions, not all possible distributions or real model performance. The conservatism is visible, not hidden. Reproduce with `python scripts/calibrate_travel_v3.py`.

The [trace projection contract](TRACE_EVIDENCE.md) describes a different, explicitly model-based source-transfer sensitivity calculation. No amount of simulation alone identifies the prevalence of previously unknown failure families in real traffic.

## Completed fresh results

Collection completed on October 24, 2026. The held-out study made **503 real requests** for **US$4.7298038**; nine reviews were skipped because their initial proposal was unavailable. The separate discovery stage made ten requests for US$0.120098, for a combined **US$4.8499018**, below the US$8 aggregate cap. All 32 registered trips completed their scheduled processing; unavailable outputs remain unavailable rather than being retried or assigned safe values. Of 503 responses, 488 were valid, seven reached max_tokens, and eight ended normally but failed local proposal validation. The latter have no archived valid proposal, so their precise validation cause is not inferred.

| Workflow | Model | Memory | Reviewer | Harmful | Task errors | Unresolved |
|---|---|---|---|---:|---:|---:|
| Original | Haiku | off | off | 2 | 5 | 2 |
| Original | Haiku | off | on | 0 | 12 | 4 |
| Original | Haiku | on | off | 0 | 4 | 3 |
| Original | Haiku | on | on | 1 | 11 | 5 |
| Original | Sonnet | off | off | 2 | 12 | 2 |
| Original | Sonnet | off | on | 4 | 9 | 3 |
| Original | Sonnet | on | off | 0 | 3 | 0 |
| Original | Sonnet | on | on | 1 | 5 | 1 |
| Grounded | Haiku | off | off | 0 | 2 | 2 |
| Grounded | Haiku | off | on | 0 | 2 | 2 |
| Grounded | Haiku | on | off | 0 | 0 | 0 |
| Grounded | Haiku | on | on | 0 | 0 | 0 |
| Grounded | Sonnet | off | off | 0 | 0 | 0 |
| Grounded | Sonnet | off | on | 0 | 0 | 0 |
| Grounded | Sonnet | on | off | 0 | 0 | 0 |
| Grounded | Sonnet | on | on | 0 | 0 | 0 |

Each row has **32 trips**, not 32 extra independent trips per arm. Task errors include harmful proposals, unnecessary escalation and unavailable responses. The same initial proposals are reused for reviewer-off outcomes. All simulated post-gate financial losses are zero because the independent gate blocks harmful proposals; unknown proposed losses remain bounded separately. No real booking or payment was attempted.

### What changed, and what remains uncertain

The original controls reproduce incorrect time comparisons, incorrect cent totals and unnecessary escalations. The grounded package produces no adjudicated harmful proposal or unnecessary escalation on this batch. Grounded Haiku without memory has two unavailable initial proposals; the other revised initial arms have none. Grounded Sonnet is not worse than Haiku on these recorded task outcomes. This does not establish a general model ranking or zero future risk.

At Sonnet/no-memory/no-review, the package avoids 12 task errors and introduces none: the paired working-model posterior reduction is **30.0 percentage points**, with marginal 95% credible interval **14.7 to 44.8 points**. Its simultaneous independent-episode bound is much wider and crosses zero. At Haiku/memory/review, it avoids 11 errors and introduces none (27.5 points; credible interval 12.4 to 42.0). These contrasts measure the **whole package**, not memory alone.

Within the original Sonnet/no-review workflow, memory avoids ten task errors and introduces one (22.5 points; credible interval 7.0 to 37.9). Within the grounded Haiku/no-review workflow, memory avoids two unavailable outputs and introduces none (5.0 points; credible interval **−5.6 to 15.4**). Grounded Sonnet shows no observed incremental memory benefit; the interval still spans about −9.4 to 9.4 points. None of these memory contrasts establishes a database-specific causal benefit.

The original reviewer introduces regressions on Haiku: two corrections versus nine introduced errors without memory, and zero versus seven with memory. The revised reviewer introduces no new observed error, but also supplies no observed incremental correction once the revised initial proposal is valid. A skipped critic cannot repair an unavailable proposal. **No incremental financial-risk reduction from the revised critic or memory is established by this small batch.** Conservative simultaneous bounds include no effect for all registered paired contrasts.

The discovery stage produced 12 candidates: two cite failed development traces and ten remain untested hypotheses. A failed-trace citation does not validate the proposed mechanism. They are not counted as held-out incidents, assigned population frequencies or automatically promoted into the case generator.

### Reproduction and artifacts

- [Full real-response study](examples/travel-v3.json) and [registered protocol](examples/travel-v3-preregistration.json).
- [Fresh error audit](examples/travel-v3-error-audit.json), with saved decisions and source IDs.
- [Discovery results](examples/travel-discovery.json) and [discovery registration](examples/travel-discovery-preregistration.json).
- `python scripts/verify_travel_v3.py docs/examples/travel-v3.json --output verification.json` independently reconstructs eligibility, policy checks, cent losses, request fingerprints, usage costs, memory sources and every posterior/bound.
- Add `--discovery` and use the discovery archive to verify its source citations, labels, requests and costs.
