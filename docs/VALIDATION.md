# Validation record

## Current automated checks

**120 automated tests passed** after the expanded failure-catalogue and interface upgrade. [Continuous integration](https://github.com/farzana0/riskgraph/actions/workflows/test.yml) runs the test suite plus original and adversarial CLI evaluations. Tests include confidence-sequence inversion and boundary behavior, exact small-horizon crossing control, restart-mixture prefix consistency, policy-disagreement fail-closed execution, review tampering, legacy evidence, and all scenario suites.

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

All orders, customers, messages, and money are synthetic. Validation covers simulated execution, tested policy invariants, and the documented provider integrations. Production payments, representative customer data, disaster recovery, policy-memory supersession, and shared memory between two application agents are outside the current scope. Policy tests do not constitute an end-to-end formal proof of the AI system.

## Expanded catalogue and revised hosted workflow

The [expanded campaign](FAILURE_SCENARIOS.md) records 28 named scenarios, 100,000 proposals, 2,856 end-to-end decisions, 25 provider faults, six memory conditions, and nine record-integrity checks. All sampled harmful proposals were blocked; all reference-authorized proposals passed. This is a synthetic fault campaign, not an estimate of Claude failure frequency.

Two new 40-case Claude runs on revision `2e30cd8`, seed `2102101`, completed with memory off and then hosted memory on. Both recorded zero harmful proposals, protocol rejections, unpaid fully eligible requests, and residual loss. All 80 reviews recomputed successfully. All 40 memory-on cases recorded recalled sources and retrieval trace IDs. The token totals were 85,764 input and 19,369 output. Their evidence is in `claude-v2-baseline.json` and `claude-v2-memory.json`. Reusing one workload with existing shared memory does not identify a causal memory benefit.
