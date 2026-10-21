# Execution and coordination failure models

These twelve specified numeric outcome models complement the reference-runtime tests. They simulate financial consequences; they are not observed defects, real payment failures, measured model error rates, or native framework benchmarks.

Seed 20261023; 10,000 completed episodes and 2,000 unresolved episodes; no provider calls.

| Scenario | Proposed loss | Loss after execution | Unresolved |
|---|---:|---:|---:|
| payment_replay | $0.00 | $750.00 | 0 |
| wrong_recipient | $0.00 | $1,725.00 | 0 |
| concurrent_balance_race | $0.00 | $4,900.00 | 0 |
| stale_policy_gate | $5,250.00 | $2,800.00 | 0 |
| fail_open_timeout | $33,000.00 | $7,000.00 | 0 |
| partial_write_recovery | $0.00 | $300.00 | 0 |
| poisoned_shared_memory | $23,475.00 | $0.00 | 0 |
| critic_false_assurance | $99,000.00 | $0.00 | 0 |
| critic_false_alarm | $0.00 | $0.00 | 0 |
| common_dependency_compromise | $475.00 | $19,000.00 | 0 |
| delegation_loop | Not identified | Not identified | 1000 |
| delayed_settlement | Not identified | Not identified | 1000 |

Each completed model has 1,000 episodes. Proposed loss can be zero while execution loss is positive: duplicate settlement, wrong recipients, state races and unsafe recovery are distinct from reasoning failures. The imported assessment supports this distinction. The reference refund gate itself does not perform those external operations.

The critic false-assurance model illustrates the authority boundary: an advisory model agreeing with a bad proposal cannot make the deterministic reference gate authorize it. The false-alarm model records service abstentions separately from unauthorized-payment loss. A common-dependency model uses history-dependent compromise probability and can affect both proposer and executor.

Delegation-loop and delayed-settlement episodes have unresolved monetary outcomes. No loss estimate is issued, and their losses are not replaced with zero. Their availability/settlement status remains separate evidence.

The ten completed scenario pairs share a 5% time-uniform interval error budget: 0.25% per stream. Each known simulation conditional-mean target lies in its reported final interval in this recorded experiment. This is one generated sequence per scenario, not an empirical coverage study. Monte Carlo coverage checks are separately reported in [ASSURANCE_RESULTS.md](ASSURANCE_RESULTS.md).

The [raw study](examples/operational-outcomes.json) includes bounds, known targets, priors, source fingerprints and scenario scope. The [payment replay episode file](examples/execution-fault-episodes.json) can be opened in the assessment intake, or selected through Stress tests → execution scenarios → Assess the payment replay example. It contains $750 simulated execution loss after correct proposals across 1,000 episodes.

Full authority model, loss definitions and research sources: [RESEARCH_DESIGN.md](RESEARCH_DESIGN.md).
