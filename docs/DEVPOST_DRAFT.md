# RiskGraph project description

**Tagline:** Risk monitoring for AI refund agents, with uncertainty estimates for small samples.

## Problem

Support operations teams need evidence before automating refunds. A small evaluation may miss rare, expensive mistakes, and zero observed failures provides limited assurance. RiskGraph makes monetary exposure and uncertainty visible while checking proposed actions before execution.

## Product

RiskGraph pairs a synthetic refund agent with an independent online safety monitor. It evaluates ordinary and adversarial cases, records proposed and executed decisions, and measures unauthorized synthetic loss prevented. The dashboard connects aggregate risk estimates to individual decisions and policy verdicts.

The estimator separates harmful-proposal frequency from positive-loss severity. Explicit Beta and Dirichlet priors retain uncertainty with few or no failures. A separate time-uniform loss bound supports repeated observation under bounded, common-mean assumptions. A betting e-process monitors proposed harm against a fixed reference rate.

## Architecture and integrations

The application uses Python, FastAPI, NumPy, SciPy, SQLite, and an HTML/CSS/JavaScript dashboard deployed on Render. Claude proposes schema-validated actions through the Messages API. SurrealDB Agent Memory stores blocked incidents and retrieves prior evidence with source, turn, and trace identifiers. Recalled text provides context without gaining authority over the independent policy monitor.

## Distinctive approach

Sparse frequency/severity estimates, sequential monitoring, pre-execution policy checks, and incident provenance are presented in one inspectable workflow. The statistical components use established mathematics with explicit priors, assumptions, and scope. Individual decisions remain traceable to synthetic order facts and policy checks.

## Validation

The automated suite contains 80 tests covering policy invariants, statistical calculations, provider contracts, replay protection, storage, and access controls.

The 40-case offline fixture produced 26 harmful proposals. The monitor blocked all 26, preventing $2,800 of unauthorized synthetic loss with zero observed residual loss. This deliberately naive fixture demonstrates policy enforcement and is separate from model evaluation.

A fresh 20-case Claude evaluation completed with two protocol-invalid escalations blocked and zero unauthorized monetary loss observed. Those escalations carried nonzero amounts but did not propose refunds, so they are not counted as prevented financial losses. Two separate three-case checks verified Claude alone and Claude with hosted incident recall. Hosted memory also stored an incident and retrieved it in a later evaluation.

Raw synthetic exports and the complete validation record are included in the repository. These samples establish integration behavior, not a production error rate or causal memory benefit.

## Scope and development direction

All customers, orders, messages, and monetary outcomes are synthetic. The severity model rounds upward into bands capped at $1,000, and sparse estimates depend on disclosed priors. Adaptive-memory runs disable the common-mean sequential bound.

Further development targets representative held-out evaluation, broader harm definitions, versioned policy memory, independently checked authorization evidence, and production identity and storage controls.

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
