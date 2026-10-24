# Memory retrieval, use and computational grounding

## What the original evidence supports

The [48-case development study](REAL_MEMORY_STUDY.md) recorded Haiku harmful proposals increasing from 2 to 4 with raw memory; task errors increased from 7 to 9. The paired accounting is one harmful proposal fixed and three introduced. All twelve memory topics had a matching real SurrealDB source, and none of the model responses was truncated. The [autopsy](examples/haiku-memory-autopsy.json) preserves the five model/memory cells whose task status or loss changed.

Two introduced harmful proposals incorrectly reduced an expired order's elapsed age to 30 days despite a correct UTC/floor hint. Another used an incorrect nested-reversal total. One memory-enabled refusal overlooked a paid total in the current connector records. Conversely, memory corrected a $4.32 reversal overpayment. Even some correct refusals without memory stated an incorrect age: the recorded decision reason is not a verified calculation or access to private reasoning.

These observations locate weaknesses in applying and grounding procedural guidance. They do **not** establish why the aggregate difference arose: one stochastic response per cell and a paired interval crossing zero leave response variability and context effects unresolved. There is no evidence here that SurrealDB itself corrupted the remembered guidance. The new protocol tests concrete remedies rather than claiming that this diagnostic identifies a causal mechanism.

## Prospective fresh-case ablation

The [registration](examples/memory-v3-preregistration.json) freezes **36 new, harder cases**, six each from elapsed-time boundaries, temporal identity, nested reversals, foreign-currency reservations, snapshot precedence and approval boundaries. Compared with the development workload, these add second-level boundary cases with fractional-hour offsets, more reversal depth/records, more reservation duplicates, sibling snapshots with misleading high sequence numbers, and failed/cancelled debit distractors. All identifiers and numeric draws are fresh. These six targeted families are not the same workload as the previous twelve-family mixture; neither report is pooled with the other.

Each Haiku and Sonnet request is tested with four strategies:

| Strategy | Retrieval and use | Current-record calculations |
|---|---|---|
| No memory | No recalled context; original policy prompt | Absent |
| Raw memory | Actual retrieved v2 family hint; original policy prompt | Absent |
| Selected memory | Capability-based planning, content/version/validity-checked sources, compact advice and an explicit usage contract | Absent |
| Memory + calculations | Exactly the selected-memory context and usage contract | Deterministic preflight support from visible records |

Every valid initial proposal receives a separate Sonnet corrective review under the same strategy. Critic-off reuses that exact initial proposal. This produces sixteen scored configurations per case, at most **576 paid calls**, and a new **$6 token-cost allowance** with persistent per-request reservations. Failed or unknown calls are not retried automatically and retain their conservative reserve. No previous account counter or study is reset. Models use the same 2,048-output-token allowance and effort settings as the development study. Configuration order is interleaved with a fixed seed. Cases, prompts, calculation code, bank, scorer, analysis and settings are fingerprinted before paid calls.

Raw→selected changes retrieval selection, representation and usage instructions jointly. Selected→calculations isolates the addition of the preflight reports within this bundle. No-memory→full-bundle measures the total intervention, **not a database-memory-only effect**. Context length and individual components of the selected-memory contract are not separately controlled. Critic effects are reported separately for each strategy.

## Retrieval and authority

The revised planner reads connector capabilities, not hidden scenario labels, scoring state or customer instructions. Timestamp fields request UTC guidance; identity bindings request sequence/join guidance; ledger event shape requests debit or reversal guidance. At most three applicable skills enter a request.

Seven authored procedural items are stored in actual SurrealDB Agent Memory under a new versioned study tag and queried back through its hybrid endpoint. The application checks source IDs, retrieval traces, the exact canonical content fingerprint, revision and validity interval, then supplies a compact canonical representation. Unrelated passages and surrounding instructions are never forwarded as guidance. These are application-level checks around the hosted memory API; they are not a claim to implement SurrealDB's native temporal-reconciliation engine. The raw-control hints are also queried from the actual prior bank. Retrieval snapshots are frozen before evaluation and shared across models and critics; browsing the graphs does not perform another query or paid call. No held-out result is written back.

The usage contract separates advice from current evidence, requires independent ownership/age/balance/approval checks, rejects remembered amounts or decisions, and asks for zero-amount escalation when required evidence is missing or contradictory. It does not request private chain-of-thought.

## Computational support

The preflight module reads only the supplied authenticated connector records and request. It calculates UTC elapsed seconds and floored days; current identity and ledger sequence joins; deduplicated active reversal debits; posted balances; and aggregate rational FX conversion. Every derived field carries source paths and the input digest. Conflicting duplicates, ambiguous latest state, wrong subjects, naive timestamps and cyclic/dangling reversal references remain unresolved. The module never reads `truth`, expected refund amounts or the scoring oracle, and it never authorizes or executes a refund.

This support is explicitly visible as a separate graph node. It is an orchestrator-run deterministic preflight, not a tool call invented after an LLM response. The model still proposes an action and the independent fixed gate retains execution authority. Calculator/parser defects are possible; tests reconstruct the held-out scoring state independently and include ambiguity controls.

## Uncertainty and endpoints

The primary financial endpoint is unauthorized **proposed** loss; residual loss after the fixed synthetic gate and task errors are separate. Underpayment/refusal cannot appear as successful service. Missing responses are unresolved financial observations and task errors. Conditional financial summaries explicitly target completed episodes, with a separate missing-loss sensitivity range.

Six fixed family weights of 1/6 combine independent Jeffreys Beta(1/2,1/2) frequency posteriors and positive-loss Dirichlet(1/4,1/4,1/4,1/4) severity models using $25/$100/$500/$1,000 upper bins. Marginal Bayesian intervals use 12,000 seeded draws. Binned posterior dollar loss is prior-sensitive and can exceed exact-dollar observed loss; it is not a production forecast. Prior sensitivity varies frequency and severity concentrations without selecting a favorable prior.

All thirty-two comparisons use matched cases: raw memory versus none, selected versus raw, calculations versus selected, full bundle versus none, critic on versus off in each mode, and Sonnet versus Haiku in each mode/review condition. Each family/comparison updates a joint four-outcome Dirichlet(1/4,1/4,1/4,1/4) model. This preserves marginal Jeffreys priors and samples the avoided-minus-introduced contrast directly, rather than subtracting independent arm samples. Positive reduction favors the second configuration; overlapping-zero intervals are inconclusive under the model.

Separate frequentist families allocate 5% to 96 family/configuration frequency upper bounds, 5% to 192 family/comparison contrasts (768 exact one-sided endpoints), 5% to 32 conditional-dollar arm/stream sequences and 5% to 32 conditional-dollar paired sequences. Fixed-batch frequency guarantees require complete outcomes, fixed policies and IID pairs within family; dollar sequences target average predictable conditional loss with bounded adapted outcomes. The four families together are **not** a joint 95% guarantee (union bound at least 80%). No production claim or guaranteed intervention benefit is prespecified.

The protocol follows current [SurrealDB hybrid retrieval](https://surrealdb.com/docs/agent-memory/retrieve/hybrid-search) and [provenance documentation](https://surrealdb.com/docs/agent-memory/mental-model/provenance-and-traceability), and the [Claude tool-use contract](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview). The statistical derivations and references remain in [METHODS.md](METHODS.md) and [MODEL_AUDIT.md](MODEL_AUDIT.md).
