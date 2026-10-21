# RiskGraph project description

**Tagline:** Risk monitoring for AI refund agents, with uncertainty estimates for small samples.

## Problem

Support operations teams need evidence before automating refunds. A small evaluation may miss rare, expensive mistakes, and zero observed failures provides limited assurance. RiskGraph makes monetary exposure and uncertainty visible while checking proposed actions before execution.

## Product

RiskGraph combines a refund proposer, a deterministic read-only policy reviewer, and an independent online safety monitor. It evaluates ordinary and adversarial cases, records proposed and executed decisions, and measures unauthorized synthetic loss prevented. The plain-language dashboard separates observed losses, payments stopped, remaining exposure, and evidence strength, with consistent icons and optional statistical detail.

The estimator separates harmful-proposal frequency from positive-loss severity. Explicit Beta and Dirichlet priors retain uncertainty with few or no failures. Beta-mixture tail confidence sequences provide time-uniform upper bounds under fixed conditional tail probabilities and a bounded loss cap. A mixture of betting rates and precommitted restart times monitors proposed harm against a fixed reference rate.

## Architecture and integrations

The application uses Python, FastAPI, NumPy, SciPy, SQLite, and an HTML/CSS/JavaScript dashboard deployed on Render. Claude proposes schema-validated actions through the Messages API. SurrealDB Agent Memory stores blocked incidents and retrieves prior evidence with source, turn, and trace identifiers. Recalled text provides context without gaining authority over the independent policy monitor.

## Distinctive approach

Sparse frequency/severity estimates, sequential monitoring, pre-execution policy checks, and incident provenance are presented in one inspectable workflow. The statistical components use established mathematics with explicit priors, assumptions, and scope. Individual decisions remain traceable to synthetic order facts and policy checks.

## Validation

The automated suite contains 149 tests covering policy invariants, confidence-sequence inversion, sequential error control, review verification, scenario generation, provider contracts, replay protection, storage, and access controls.

The 40-case offline fixture produced 26 harmful proposals. The monitor blocked all 26, preventing $2,800 of unauthorized synthetic loss with zero observed residual loss. This deliberately naive fixture demonstrates policy enforcement and is separate from model evaluation.

A fresh 20-case Claude evaluation completed with two protocol-invalid escalations blocked and zero unauthorized monetary loss observed. Those escalations carried nonzero amounts but did not propose refunds, so they are not counted as prevented financial losses. Two separate three-case checks verified Claude alone and Claude with hosted incident recall. Hosted memory also stored an incident and retrieved it in a later evaluation.

Raw synthetic exports and the complete validation record are included in the repository. These samples establish integration behavior, not a production error rate or causal memory benefit.

The current local framework study sampled 50,000 policy proposals, including 25,767 harmful proposals, with no harmful bypass. It also completed 3,440 workflow decisions and 120,000 monitoring trajectories. At a 15% harm rate, alarm detection within 500 observations increased from 17.34% to 80.19%; measured null false alarms were 2.31%. Strong early signals can trigger more slowly with the mixture. These simulations are separate from the earlier Claude API checks.

The expanded catalogue adds 28 named failure and boundary scenarios across identity, manipulation, payments, and combined violations. Its separate campaign tested 100,000 policy proposals and 2,856 workflow decisions, plus 25 provider faults, six memory conditions, and nine integrity checks. No harmful proposal passed and no reference-authorized proposal was incorrectly blocked in that synthetic campaign. Two new 40-case Claude evaluations of the revised workflow completed with zero harmful proposals and residual loss; all reviews verified, and all memory-on cases recorded actual hosted retrieval sources and traces.

## Scope and development direction

All customers, orders, messages, and monetary outcomes are synthetic. The severity model rounds upward into bands capped at $1,000, and sparse estimates depend on disclosed priors. Adaptive-memory, designed-catalogue, workload-shift, and correlated suites disable stationary confidence bounds.

Further development targets representative held-out Claude evaluation, broader harm definitions, versioned policy memory, and production identity and storage controls. Current decision evidence is recomputable from recorded facts; this is not a formal proof of the complete AI system.

## Development attribution

Developed for Build North 2026 with AI coding assistance from Codex. The interface and synthetic scenarios are project-specific. Established statistical methods and open-source dependencies are documented in the repository; no external UI template or customer dataset is used.

## Project links

- [Live application](https://riskgraph-fa98.onrender.com)
- [Source repository](https://github.com/farzana0/riskgraph)

## Suggested demonstration sequence

1. Introduce the refund-automation problem and identify the synthetic evaluation mode.
2. Inspect a prompt-injection or duplicate-refund proposal and its policy verdict.
3. Compare observed loss, posterior uncertainty, and the conservative upper bound.
4. Open a stored incident and a later memory recall with source and trace identifiers.
5. Show a Claude evaluation, evidence export, and the documented validation scope.
