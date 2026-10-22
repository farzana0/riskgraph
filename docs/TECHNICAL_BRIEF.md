# RiskGraph technical review brief

RiskGraph measures financial exposure at the level of a complete agent workflow episode. It separates unsafe proposals, executed loss, uncertain mean risk, and operational failures that have no adjudicated financial outcome.

## Demonstration

1. Open **Assess risk**. The featured controlled refund example contains $6,914.98 of unauthorized proposed exposure across 56 episodes. The gate stops the harmful proposals; observed execution loss is zero. Estimated mean risk remains nonzero under the stated prior.
2. Open reviewed JSON/JSONL logs. Multiple agent messages share one episode ID and one final reviewed loss pair. Missing outcomes and duplicate final records are rejected. Numeric analysis is stateless; raw messages remain in the browser.
3. Open **Stress tests**. The payment-replay example has correct proposals but $750 simulated execution loss. Delayed settlement and delegation-loop scenarios have unresolved outcomes, not zero loss.
4. Review the paired model results and one decision trace. Policy checks, role handoffs, memory sources, model advice and executed accounting can be inspected separately.

## Architecture and mathematical claims

A proposer model and optional advisory critic consume trusted case facts and untrusted contextual data. Deterministic review and the payment gate retain execution authority. Case-bound receipts and ledger transactions support consistency/replay checks. The reference runtime is explicit and framework-neutral; openJiuwen is the leading optional Python orchestration candidate, with Hermes and OpenClaw considered future systems under test.

A Beta-frequency/Dirichlet-severity model describes mean upward-binned loss and prior sensitivity. A normal-mixture Hoeffding confidence sequence bounds average conditional expected loss over observed episodes, permitting adaptive dependence. It does not forecast an arbitrary future workload. Fixed-tail bounds require stronger assumptions. Monetary and frequency e-processes monitor different conditional nulls and carry separate error budgets.

Z3 establishes a restricted policy-kernel property: no action allowed by the encoded current gate has positive specified unauthorized-payment loss. Six removed-guard controls yield counterexamples; 2,000 concrete examples check encoding/Python alignment. The translator, solver, typed inputs and policy specification remain trusted. This is not an end-to-end proof of agent or payment-system safety.

## Recorded findings

- **Harder tool-record comparison:** 32 held-out cases per configuration expose real model mistakes. Without memory, Haiku makes four task errors and Sonnet one. The critic fixes three Haiku task errors but introduces one; for Sonnet it fixes one and introduces two. Memory and critic effects interact. A separate 16-case higher-response follow-up has no truncations: Haiku task errors fall from 3 to 1 with critic, 2 with memory, and 0 with both; Sonnet falls from 1 to 0 with either. Token exhaustion and unresolved primary financial outcomes are reported separately; [full factorial results](HARD_BENCHMARK.md) retain both improvements and regressions.
- **Two-model integration:** a three-episode hosted smoke test completed with Haiku proposals, Sonnet advisory reviews and actual SurrealDB retrieval. All reviews and handoffs verified. This establishes the integration path, not the critic's effectiveness.
- **320 matched-case model decisions:** Haiku and Sonnet each process 160 cases across all 28 scenario categories. Both produce zero harmful proposals in this experiment. No superiority or equivalence conclusion follows.
- **Uncertainty after zero losses:** each model retains a $1.26 posterior mean binned loss per episode under the same prior. A separate bounded interval for the matched conditional mean loss difference spans approximately −$240.34 to $240.34. The conservative width exposes the evidence limit.
- **50,000 monitoring trajectories:** a severity-only shift triggers the monetary alarm on 100% of paths versus 2.66% for the frequency alarm. Rare 2%-frequency $1,000 losses trigger the monetary alarm only 28.38% by episode 500, a clear power limitation.
- **Policy conformance campaign:** 100,000 sampled proposals, 26,427 harmful proposals and zero harmful allowed actions. This is conformance to the implemented synthetic specification, not a measured production failure rate.

## Research position and next validation

The contribution is an integrated assurance prototype applying published statistical and evaluation methods, with reproducible evidence and explicit claim boundaries. It does not claim a new concentration theorem or published validation of RiskGraph itself.

The next research step is independent held-out workloads and attack families, audited real-world episode labels, variance-adaptive inference, distributed execution verification, and matched critic/memory ablations. The current structured refund benchmark does not discriminate model monetary risk. Framework security rankings, production premiums, unbounded loss tails and causal memory benefits remain unestablished.

Full sources, assumptions and reproduction: [research specification](RESEARCH_DESIGN.md), [framework decision](FRAMEWORK_DECISION.md), [paired comparison](PAIRED_MODELS.md), [monitoring study](ASSURANCE_RESULTS.md), [policy verification](POLICY_VERIFICATION.md), and [execution models](OPERATIONAL_SCENARIOS.md).
