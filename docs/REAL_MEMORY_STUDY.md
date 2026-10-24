# Real-model memory and critic study

This is a separate, prospectively specified 48-case challenge study, not an extension selected from successful historical examples. Twelve families have four independently seeded cases each. The original eight tool-record families are augmented with nested reversal chains, deduplicated foreign-currency reservations, temporal identity joins, and one-cent approval-boundary reconstruction. Cases, memory text, scorer, analysis and request settings are fingerprinted in [the registration](examples/research-v2-preregistration.json) before calls. All identities, records, money and payment outcomes are synthetic. Model proposals and SurrealDB retrieval are real.

Each case receives four initial requests: Haiku/Sonnet × memory off/on. A separate Sonnet corrective critic reviews each valid initial proposal. The critic-off condition reuses the initial proposal, giving eight scored configurations per case and at most 384 paid requests. Configuration order is seeded and interleaved. All proposals are scored against withheld canonical state and the same independent simulated gate. No real payment tools are available. The critic can introduce errors. Eligible underpayment and unnecessary refusal remain task errors.

The new model-call allowance is at most $5, with persistent reservations before calls and no automatic retry for failed or unknown requests. Token prices were checked against the [official pricing page](https://platform.claude.com/docs/en/about-claude/pricing) on October 24, 2026. The allowance is a token-cost accounting limit, not a provider invoice, prepaid balance or SurrealDB usage cap. Existing application and historical research counters are preserved.

## SurrealDB intervention

Before the first model call, twelve generic procedural hints are written to the configured Agent Memory scope under a new study tag. Each is queried back through the actual hosted API; matching source text, source IDs, write-turn IDs and retrieval trace IDs are retained. Retrieval without matching provenance pauses the study. Hints contain no test IDs, answer amounts or scored outcomes. The retrieved snapshot is frozen and identical across models; no test outcome is written back. This measures the total effect of supplying this particular retrieved bank, including extra context and stochastic responses. It does not isolate a database-specific benefit or establish universal memory effectiveness. Source APIs follow the [hosted memory contract](https://surrealdb.com/docs/agent-memory/quickstarts/hosted).

## Statistical specification

The target workload gives each of the twelve challenge families weight 1/12. These are explicit challenge weights, not measured production traffic. Within each family/configuration, a Jeffreys Beta(1/2,1/2) prior updates with k harmful proposals among n resolved outcomes. Posterior frequencies are averaged using the fixed weights, with 12,000 seeded draws for each marginal 95% credible interval. Missing responses do not become safe outcomes. Four observations per family leave substantial prior influence even when no harm is observed.

Positive monetary severity is upward-binned to $25, $100, $500 or $1,000 with a Dirichlet(1/4,1/4,1/4,1/4) prior. Within each family the frequency draw multiplies a severity draw; the weighted sum gives posterior mean binned proposed loss. It differs from exact-dollar observed loss and may be much larger for sparse, cent-scale mistakes. Priors are working assumptions; Bayesian coverage and generalization are not guaranteed by the display.

Every intervention uses matched case outcomes. For each family/comparison let q=(both harmful, avoided, introduced, neither harmful). The joint prior is Dirichlet(1/4,1/4,1/4,1/4), preserving Jeffreys Beta marginal priors. Updating the four cell counts and sampling q10−q01 directly preserves within-pair dependence. Positive reduction favors the intervention. Critic comparisons hold memory/model fixed; memory comparisons hold model/critic fixed. Model comparisons hold both interventions fixed. No subtraction of independent arm samples is used for contrast intervals. Marginal intervals across comparisons do not constitute simultaneous Bayesian coverage.

Separate frequentist checks remain available. Exact one-sided Clopper–Pearson upper bounds allocate .05/96 across 12 families × 8 configurations. For the twelve matched frequency comparisons, separate upper/lower bounds for both discordant probabilities allocate .05/576 over 12 families × 12 comparisons × 4 endpoints. The weighted signed interval is the sum of [L10−U01,U10−L01]/12. These require the complete fixed batch, fixed policies and IID pairs within a family. They remain deliberately wide at four cases per family.

Adaptation-tolerant normal-mixture Hoeffding confidence sequences additionally bound conditional mean dollar loss and signed paired dollar reduction. Sixteen arm/stream intervals share another 5% family; twelve dollar contrasts another 5% family. Signed differences are shifted from [−$1,000,$1,000] to [0,$2,000]. These targets describe conditional averages over completed observed episodes, not arbitrary future traffic. The four frequentist families together are **not** a joint 95% guarantee (union bound at least 80%). The derivation is in [METHODS.md](METHODS.md); see [Howard et al., Annals of Statistics 2021](https://doi.org/10.1214/20-AOS1991).

An interval crossing zero is inconclusive, regardless of the observed improvement. Every report retains harmful proposals avoided and introduced, task errors fixed and introduced, incomplete pairs, actual recorded source evidence, token usage and estimated costs. No result is assumed to favor memory, the critic or the larger model.

## Completed results · October 24, 2026

The registered design was published as `59e57b8` before calls. All 48 cases completed in all configurations: 192 model/memory cells, 384 unique model calls and 384 adjudicated stage outcomes, with no provider error, invalid response, truncation or paid retry. Twelve actual SurrealDB retrieval snapshots contain matching source IDs and trace IDs. The token-cost estimate is **$2.9592**, below the $5 allowance.

| Model | Memory | Critic | Harmful proposals / 48 | Task errors / 48 | Proposed unauthorized loss |
|---|---|---|---:|---:|---:|
| Haiku | Off | Off | 2 | 7 | $114.08 |
| Haiku | Off | On | 0 | 1 | $0.00 |
| Haiku | On | Off | 4 | 9 | $511.03 |
| Haiku | On | On | 0 | 0 | $0.00 |
| Sonnet | Off | Off | 3 | 3 | $599.97 |
| Sonnet | Off | On | 0 | 0 | $0.00 |
| Sonnet | On | Off | 0 | 0 | $0.00 |
| Sonnet | On | On | 0 | 0 | $0.00 |

All observed residual losses after the fixed independent simulated gate were zero. That does not turn proposed harm, service errors or future execution risk into zero.

| Intervention | Model / context | Observed frequency reduction | Joint posterior reduction [95% credible], percentage points | Harm avoided / introduced |
|---|---|---:|---:|---:|
| Critic | Haiku, memory off | +4.17 pp | +3.33 [-4.97, +11.65] | 2 / 0 |
| Critic | Haiku, memory on | +8.33 pp | +6.67 [-2.20, +15.53] | 4 / 0 |
| Memory | Haiku, critic off | -4.17 pp | -3.33 [-12.40, +5.62] | 1 / 3 |
| Memory | Haiku, critic on | +0.00 pp | +0.00 [-7.37, +7.29] | 0 / 0 |
| Critic | Sonnet, memory off | +6.25 pp | +5.00 [-3.32, +12.87] | 3 / 0 |
| Critic | Sonnet, memory on | +0.00 pp | +0.00 [-7.37, +7.29] | 0 / 0 |
| Memory | Sonnet, critic off | +6.25 pp | +5.00 [-3.32, +12.87] | 3 / 0 |
| Memory | Sonnet, critic on | +0.00 pp | +0.00 [-7.37, +7.29] | 0 / 0 |

Every paired Bayesian credible interval crosses zero; all conservative frequentist contrast intervals also include zero. The sample therefore does not establish a general memory/critic benefit or a model ranking. Observed reductions remain valid descriptions of this finite challenge set.

Sonnet without either intervention proposed three unauthorized $199.99 refunds on expired temporal-identity cases. Both memory-enabled initial requests and corrective review avoided these proposals. The graph can expose the specific prior hint (highest-sequence identity binding plus UTC elapsed-time calculation), source chunk ID and retrieval trace beside each saved decision.

Haiku illustrates the opposite outcome: memory fixed one harmful case and introduced three, increasing harmful proposals from 2 to 4 and proposed loss from $114.08 to $511.03. Its mistakes include a $4.32 nested-reversal overpayment without memory, $1.29 overpayment with memory, and time-window violations. Without memory its critic fixed seven task errors but introduced one new service error. With memory the critic fixed all nine task errors and introduced none. This prevents the interface from presenting memory or criticism as uniformly effective.

The zero-harm configurations retain a 10.0% weighted posterior frequency mean with a 95% credible interval of approximately 4.2–17.8%: only four observations support each of twelve independent family posteriors. The corresponding $40.63 mean binned loss per case is strongly prior-influenced, with upward severity bands and an unobserved severity distribution. It is not measured dollar loss. Conservative bounds remain much wider.

[Raw frozen report](examples/research-v2.json) · [independent recomputation](examples/research-v2-verification.json). Reproduce verification with `python scripts/verify_research.py docs/examples/research-v2.json --output evidence/research-v2-verification.json`. No provider request is made by the verifier or the public graph views. Historical studies remain separately accessible in the evaluation workspace.
