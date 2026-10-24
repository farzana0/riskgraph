# Validation record

## Current automated checks

**158 automated tests passed** after the episode-level assurance, symbolic policy, execution-scenario and harder factorial benchmark upgrades. [Continuous integration](https://github.com/farzana0/riskgraph/actions/workflows/test.yml) runs the test suite plus original and adversarial CLI evaluations. Tests include confidence-sequence inversion and boundary behavior, exact small-horizon crossing control, restart-mixture prefix consistency, policy-disagreement fail-closed execution, review tampering, legacy evidence, and all scenario suites.

The earlier 80-test suite and provider-integration evidence below were recorded on revision `540d8c86674d0ea1b48ac118fd6cd3a9417f6862`. Those October 18 results remain historical evidence. The [current comparison](FRAMEWORK_V2.md) records the local framework upgrade; fresh hosted-provider validation of the revised prompt and review workflow is recorded below and in [FAILURE_SCENARIOS.md](FAILURE_SCENARIOS.md). Container execution remains outside this validation record.

Coverage includes:

- Strict money validation, policy boundaries, and a seeded 1,000-case × six-amount invariant check: no scored harmful refund passes the monitor in that check.
- Prior-only and zero-failure uncertainty; posterior identities; severity-band rounding; invalid-loss rejection.
- Hoeffding alpha spending, three sets of 1,500 simulated full trajectories, and betting e-process behavior. Simulations are checks, not a universal proof of implementation correctness.
- Claude request/response contracts, usage accounting, strict schema adaptation, local constraint validation, missing/truncated/wrong tool output, and timeouts.
- Explicit Anthropic workspace headers, cached read-only Default lookup, and rejection of archived/invalid/ambiguous/non-default/incompletely listed choices.
- Agent Memory routes, scope/lens, fact idempotency, trace/turn provenance, recall passed to the agent, and explicit read/write failures.
- Preparation of an explicitly missing demo scope using existing grants, one identical idempotent write retry, and no scope registration/retry on unrelated errors or grant escalation when registration is denied.
- Operator verification without provider calls or side effects; cross-origin rejection; export; replay protection; database reopening; persisted failed-call budgets and atomic reservations across connections.
- Redacted provider details visible only in an authenticated operator error response, never in public run/export evidence. Provider keys, operator tokens, and provider URLs are removed before the private display.

JavaScript syntax and Python compilation checks passed. The Render Blueprint passed the official JSON schema at `https://render.com/schema/render.yaml.json`; this is a configuration check, separate from the live deployment checks below.

## Reproducible offline fixture results

| Run | Seed | Cases | Harmful proposals | Blocked | Synthetic loss prevented | Observed residual loss |
| --- | --- | --- | --- | --- | --- | --- |
| Offline naive fixture, memory off | 42 | 40 | 26 | 26 | $2,800 | $0 |
| Offline fixture, local memory on | 42 | 40 | 21 | 21 | $2,450 | $0 |
| Offline naive fixture, memory off | 42 | 80 | 42 | 42 | $5,775 | $0 |

These deliberately stressful workloads and the deliberately naive fixture do not measure Claude's error rate. Local memory makes the fixture escalate later injection cases; the lower prevented-loss total reflects fewer harmful proposals needing to be blocked. This is an illustrative comparison, not a causal study of hosted memory.

For the 40-case memory-off demo, posterior proposed mean binned loss is $140.79/decision. With zero residual harm observed, posterior residual mean remains $4.95, with a 95% interval approximately $0.003–$30.26. The separate conservative residual upper bound is $368.63/decision. Display rounding can show a lower endpoint of $0.00; the posterior is not a point mass at zero. Adaptive-memory runs disable the common-mean sequential bound.

Raw 40-case examples are in `docs/examples/`. Reproduce the 80-case fixture with `python scripts/evaluate.py --seed 42 --cases 80 --output evidence/offline.json`.

## Verified live integrations

The [Render application](https://riskgraph-fa98.onrender.com) completed Claude evaluations using explicit workspace selection. Authentication credentials remain server-side and are excluded from public evidence. Rejected provider requests produce no observations and are excluded from sample sizes while consuming the persisted attempt budget.

| Evidence | Run ID | Result |
| --- | --- | --- |
| Claude, seed 901, memory off | `9c455599d86f4df199c3d7685618df14` | 3/3 valid decisions; 2,459 input and 683 output tokens; zero harmful proposals and zero residual harm observed |
| Claude + hosted memory, seed 902 | `bdb275b2531d43d4a21e9864ba5412d5` | 3/3 valid decisions; 3,611 input and 782 output tokens; actual recalled incident hits and retrieval trace IDs; zero harmful proposals and zero residual harm observed |
| Fresh Claude evaluation, seed 20261018, memory off | `6b252393dd404d5d8bfcb75455e038f6` | 20/20 decisions; 16,435 input and 4,911 output tokens; two inconsistent escalations blocked; zero unauthorized monetary loss observed |
| Hosted memory write, offline agent | `dd7a8fa481334ae0872e699cc6bc247d` | Missing demo scope prepared using existing authority; blocked incident stored with turn ID `kb0vqkk8tmy7nnu09bc7` |
| Later hosted memory recall, offline agent | `5bb6d0f7e5e84aa08c9e4b541c57003b` | Recalled the prior incident text, `memory_chunk:sreu9hdaeqnkgvubby3v`, an extracted event entity, and retrieval trace IDs; new blocked incident also stored |

Completed, public synthetic exports are saved as `docs/examples/claude-smoke.json`, `claude-memory.json`, `hosted-memory-write.json`, `hosted-memory-recall.json`, and `claude-evaluation-20.json`. They contain no provider credentials or private troubleshooting messages. The live smoke runs establish connectivity and the integration path; three cases per configuration cannot establish a production error rate or prove a benefit from memory.

The fresh 20-case seed was chosen before that evaluation and was separate from the development/smoke seeds. Its two blocked decisions were high-value escalations carrying nonzero `amount_cents` (100,000 and 50,000), which violate the monitor's `non_refund_amount` contract. They were not unauthorized refund attempts: the monetary scoring function assigns zero loss to an escalation, and execution sends no payment. Protocol rejections are reported separately from monetary harm and prevented loss.

For this 20-case sample, the residual posterior mean binned loss remains **$9.67 per decision**, with 95% credible interval **$0.0054–$57.86**, despite $0 observed loss. The separate conservative anytime upper bound is **$486.95** under its documented bounded/common-mean assumptions. These numbers are prior-sensitive synthetic estimates, not forecasts of business losses. No unnecessary abstentions were recorded by the demo's ground-truth metric. The three completed Claude runs account for 26 model decisions; the persisted budget records 31 attempts, including five earlier rejected requests.

## Browser and deployment checks

The deployed health, dashboard, assets, audit/export, and unauthenticated mutation rejection were checked. The original 40-case run `4b986541db4d4808af699ceac169dd33` remained available across multiple code and environment redeploys. Disaster recovery is outside the tested scope.

Browser QA covered new/continue evaluation controls, history, full/blocked ledger, decision traces, methods, verified operator access, errors inside the run dialog, persistent failure messages, and evidence download. Desktop 1,440 × 1,000, the narrow preview, and mobile 390 × 844 layouts were checked; tables scroll inside their containers. Exported integration evidence is included in `docs/examples/`.

## Broader synthetic simulations

The [original study](SIMULATIONS.md) records 20,000 policy proposals, 1,600 workflow decisions, 15,000 estimator datasets, and 200,000 trajectories. Its coverage and alarm-power findings motivated the upgrade. The [current framework study](FRAMEWORK_V2.md) adds 50,000 policy proposals, 3,440 workflow decisions, 80,000 paired alarm trajectories, and 40,000 bound trajectories. It verifies tighter bounds, stronger moderate-rate detection, explicit tradeoffs, and policy enforcement. Both studies are reproducible and make no provider requests.

## Remaining limits

All orders, customers, messages, and money are synthetic. Validation covers simulated execution, tested policy invariants, and the documented provider integrations. Production payments, representative customer data, disaster recovery, and policy-memory supersession are outside the current scope. The two-model memory integration below checks shared retrieved context, not coherent concurrent writes by autonomous agents. Policy tests do not constitute an end-to-end formal proof of the AI system.

## Expanded catalogue and revised hosted workflow

The [expanded campaign](FAILURE_SCENARIOS.md) records 28 named scenarios, 100,000 proposals, 2,856 end-to-end decisions, 25 provider faults, six memory conditions, and nine record-integrity checks. All sampled harmful proposals were blocked; all reference-authorized proposals passed. This is a synthetic fault campaign, not an estimate of Claude failure frequency.

Two new 40-case Claude runs on revision `2e30cd8`, seed `2102101`, completed with memory off and then hosted memory on. Both recorded zero harmful proposals, protocol rejections, unpaid fully eligible requests, and residual loss. All 80 reviews recomputed successfully. All 40 memory-on cases recorded recalled sources and retrieval trace IDs. The token totals were 85,764 input and 19,369 output. Their evidence is in `claude-v2-baseline.json` and `claude-v2-memory.json`. Reusing one workload with existing shared memory does not identify a causal memory benefit.

The subsequent live catalogue pair adds 56 Claude decisions across all 28 named scenarios, with memory off/on. All 56 reviews verified, all 28 memory-on cases recorded actual retrieval sources and traces, and no harmful proposal, protocol rejection, unpaid fully eligible request, or residual loss was observed. The revised workflow therefore has 136 completed real Claude decisions before the focused follow-up. [Evidence and scope](FAILURE_SCENARIOS.md).

The [featured injected-failure demonstration](CONTROL_DEMO.md) intentionally produces nonzero loss at risk: $6,914.98 across 48 harmful proposals in 56 decisions. All are blocked; eight valid proposals execute. Four fully eligible requests remain unpaid because the injected proposer gives the wrong amount, a separately reported service tradeoff. These are controlled failures, not measured Claude mistakes.


## v0.4 episode-level assurance extension

The stateless assessment intake accepts numeric adjudicated episode losses and a prespecified cap. The browser rejects duplicate final records, incomplete episodes and missing losses; intermediate agent messages are not independent observations. Adaptive conditional-mean confidence sequences and monetary-loss monitoring are documented in [the research specification](RESEARCH_DESIGN.md). The new [50,000-trajectory study](ASSURANCE_RESULTS.md) uses 25 million observations.

The optional second-model critic is a separate model request with advisory authority. Deterministic policy review and the gate remain distinct components. Hash receipts bind case, stage, role and executed accounting; they are consistency evidence, not signed provenance or process isolation. The reference runtime does not embed an external orchestration SDK.


The [paired real-model campaign](PAIRED_MODELS.md) completed 320 cases: 160 Haiku 5.5 and 160 Sonnet 5.5, each covering all 28 categories across four seeds. No harmful proposal, residual loss or fully eligible unpaid request was observed. All reviews and handoffs verified. The negative result does not establish equivalence; the derived analysis retains nonzero uncertainty and flags a degenerate zero-width bootstrap.

The [symbolic policy check](POLICY_VERIFICATION.md) returned UNSAT for allowed-and-positive-loss, with six guard-removal counterexamples and 2,000 differential examples. The [operational models](OPERATIONAL_SCENARIOS.md) distinguish 10,000 complete financial episodes from 2,000 unresolved episodes and permit execution loss greater than proposed loss.

A first two-model integration run completed one case, then rejected a critic response on the next case before execution. The [archived failed-run evidence](examples/critic-schema-rejection.json) is preserved. The corrected critic prompt states its explanation-length limit explicitly and has a new contract version. New runs retain aborted-stage records across retries and disable fixed-tail inference after selection or abortion.

## Corrected two-model and hosted-memory smoke test

On deployed revision `6e4293b` (v0.4.1), seed `2102122` completed three episodes with Haiku 5.5 proposing and Sonnet 5.5 making a separate advisory model request. Both models received the same retrieved context; the critic also received the proposal. All three episodes recorded `surreal_recalled`, three source hits and a retrieval trace ID. Policy reviews and handoff receipts verified both through the live endpoint and by local recomputation of the archived export. No aborted attempt, harmful proposal or residual financial loss was observed.

The six model calls consumed 7,642 input and 2,057 output tokens in total. The persistent attempt counter increased from 491 to 497, including both proposer and critic calls. This is a connectivity and contract test, not an estimate of critic effectiveness or a causal memory benefit. The earlier rejected run remains part of the evidence rather than being replaced by the successful result. [Completed export](examples/two-model-memory-smoke.json) · [verification](examples/two-model-memory-verification.json).

[Release CI](https://github.com/farzana0/riskgraph/actions/runs/39683118297) passed all 149 tests, the symbolic gate check and three CLI evaluations. Hosted checks confirmed v0.4.1, the paired-model analysis, policy artifact and operational/monitoring studies. Browser checks on the released page confirmed the refund example, the payment-replay assessment with $750 execution loss, and a 390 × 844 viewport without horizontal page overflow.


## Harder matched model and intervention experiment

The [frozen tool-record benchmark](HARD_BENCHMARK.md) processes 32 held-out cases with Haiku/Sonnet, memory off/on and a separate corrective critic off/on. Real model outputs include unauthorized time-boundary refunds, underpayments and exhausted response budgets. All 256 stage outcomes and the full statistical analysis were recomputed offline. The primary study used 251 held-out requests plus 64 development requests, with no automatic retries. Its source fingerprints match revision `1337da3`. Completed monetary outcomes and operational non-completions remain separate. A higher-response-budget follow-up is registered separately and will not be pooled with these findings.

The separate higher-response follow-up completed all 128 stage outcomes on 16 new cases, with no invalid/truncated response and no retries. Its case/source fingerprints and frozen retrieved memory matched the prior registration. Both reports, all 384 held-out stage outcomes (including unresolved primary outputs) and the statistical summaries were checked offline. Combined primary/development/follow-up model usage was 443 requests at an estimated $2.8890. [Detailed results, uncertainty and limitations](HARD_BENCHMARK.md).

## Paired workflow and Beta–Binomial demo (v0.6.0)

Local verification on 23 October 2026 completed **168 tests**, including ten new paired-demo tests. The symbolic gate check again returned UNSAT for the restricted allowed-and-positive-exposure property, with six removed-guard counterexamples and 2,000 differential checks. The existing 80-case, 40-case adversarial, and 56-case full-stress CLI checks completed with zero residual exposure under the existing gate. These checks do not validate a production risk distribution.

The saved paired demo contains 60 held-out scripted cases (ten per mutually exclusive family), 12 separate development cases, three separate curated teaching/fault examples, and three separately replayed archived real-model outputs. With the default illustrative traffic mix, weighted observed failure frequency is 23.6% without monitoring, 5.3% with the scripted reviewer, and 0% with either rule-enabled setup. Observed exposure per request is $30.44, $5.97, and $0.00 respectively. Rule-enabled setups still have an 8.33% posterior mean and a 46.06% simultaneous fixed-sample upper endpoint. The held-out seed was not changed to force reviewer false positives; that mechanism is demonstrated only by a labeled curated example.

Browser checks at 1280×900 and 390×844 confirmed executed-edge packets and node states, keyboard activation of rule evidence, replay without duplicate observations, setup switching without count changes, complete-batch projection values, traffic-weight validation, and prior/posterior density labels. The curated payment timeout shows four unresolved arm outcomes and only eight completed outcomes across three paired cases. Expanded provenance, the graph's local scroll area, and the comparison table stay within a 390-pixel page width. Reduced motion is implemented through the system media preference and disables the moving packet; this preference was inspected in code, not emulated in browser QA. No external screen-reader audit was performed.

The one-command `./scripts/start-demo.sh` was exercised from a fresh local virtual environment, installed the pinned dependencies, and started the app on port 8765. No paid model calls were made for this upgrade. [Design, assumptions, and demo script](PAIRED_DEMO.md).

## Integrated topology, explanatory replay, and paired statistical audit (v0.7.0)

The Claude topology design, controller, CSS, SVG source assets, step captions, seek rail, payload packets, ledger annotations, and guided risk-model walkthrough are integrated into the homepage and `/demo`; the earlier assessment tools remain at `/workspace`. Production uses the existing canonical evidence and analysis endpoints; the offline preview snapshot fallback was removed. Saved complete paths are visible before admission, but seeking and setup switching do not add observations. The production adapter restores keyboard focus on inspector close, labels raw event state separately from derived decisions, exposes evidence controls in both views, and connects assumed weights and posterior summaries as separate inputs to the projection calculation.

The statistical audit adds a four-outcome Dirichlet–multinomial model for each matched reference/monitor pair. Its marginal priors remain Beta(a,b), and the complete-cohort posterior means match the existing Beta–Binomial marginals. It reports weighted risk-reduction credible intervals using joint paired draws, analytic variance, prior sensitivity, discordant outcome counts, and separate conservative frequentist contrast intervals with a 72-endpoint error allocation. Those contrast bounds have a separate 5% error family; together with the original 24-cell frequency bounds they are not a joint 95% guarantee. Missing/error pairs remain unresolved. [Derivations, assumptions, and checks](MODEL_AUDIT.md).

Six new statistical tests check direct exact-binomial references, exhaustive small multinomial coverage, matching/deduplication, introduced harm, unresolved cohorts, prior sensitivity, posterior moments, and agreement with a 100,000-draw direct Dirichlet reference. The full suite contains **174 tests**.

The [calibration record](examples/paired-model-calibration.json) contains 12,000 known-truth datasets: 2,000 independent repetitions for each of two case counts and three within-case dependence settings. Exact frequency-family coverage ranged from 98.45% to 99.80%; the separate paired contrast-family coverage ranged from 99.50% to 99.85%. The equal-budget Hoeffding comparison and Monte Carlo intervals are recorded. Bayesian cell-interval and weighted joint-contrast coverage are reported separately; they are not automatically 95%. The joint calibration uses 1,000 posterior draws per dataset, versus 12,000 in the app. These are estimator simulations, not measured model/agent performance or production calibration.

Browser QA with the live local backend checked desktop 1440×900 and mobile 390×844 layouts, exact rule evidence, guided posterior captions, step seeking without admission, valid and invalid traffic edits, and separate recorded-real replay with a custom Beta(2,3) prior. The curated timeout showed 8 completed outcomes out of 12 records, four unresolved errors, and an unavailable fixed-batch upper bound. A long curated-source label initially caused 11 pixels of page overflow; responsive wrapping and the data-reference label position were corrected and rechecked at 390 pixels. An intentional backend outage retained the prior verified projection with an explicit stale-results label; restoring the backend and reapplying weights recovered successfully. Reduced-motion behavior was inspected in source; no new browser emulation or screen-reader audit is claimed.

No paid model requests were used for this integration or the statistical calibration. The frozen held-out evidence digest is unchanged.

## Real-model compound memory study (v0.8.0)

A prospectively registered 48-case, twelve-family Haiku/Sonnet factorial study completed 384 real model requests. All 384 saved stage outcomes, source fingerprints, matching keys, response identities, usage-accounted costs and the full stratified/joint analysis recompute offline. Actual SurrealDB source hits and traces are preserved for all twelve families. Four new tests independently reconstruct compound oracles, check the joint model and exact endpoints, retain introduced harm/unresolved outcomes and check the public read-only report. The full suite has **178 tests**. [Protocol, mixed results and uncertainty](REAL_MEMORY_STUDY.md).

The new `/study` request topology and probabilistic graph use saved evidence, expose both memory corrections and regressions, and distinguish proposed financial harm from gate residual loss and task errors. Browser checks cover desktop and 390px phone layouts, trace inspection, keyboard dialog focus, model/setup/example switching, matched-interval displays and explicit unresolved labels. No paid requests are triggered by graph navigation.


## Memory retrieval and calculation ablation (v0.9.0)

A prospective 36-case experiment evaluates four memory strategies, two models and separate corrective reviews. It records 575 real model requests ($5.8471044 estimated token cost), 574 resolved stage outcomes and two explicit unresolved stages from one truncated Haiku proposal and its skipped critic. The independent verifier reconstructs all original request hashes, 575 unique recorded response identities, seven SurrealDB source selections, 49 rejected hits, all 36 record-calculation reports, scored outcomes and all 32 matched comparisons. The frozen source hashes and original 48-case study remain unchanged. [Results, uncertainty and limitations](MEMORY_INVESTIGATION.md).

Eight new tests cover independent reconstruction from visible records, ambiguous/conflicting inputs, source validity/content/trace checks, capability-based planning, prompt authority boundaries, matched comparisons, missing outcomes and read-only study access. The full suite contains **186 tests**. The versioned research runner exercises the revised agents; the simpler legacy evaluation lab retains its earlier protocol.

The new `/study` topology separates source retrieval, deterministic calculations, initial proposal, corrective critic and execution authority. The risk view shows raw→selected, selected→calculations, full-bundle and critic contrasts with matched credible intervals, plus separate conservative bounds, prior sensitivity and missing-data ranges. The original graphs are retained at `/study?experiment=original`. Navigation makes no paid requests.
