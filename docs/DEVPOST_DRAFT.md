# RiskGraph

**Tagline:** Know the cost of an AI agent's mistakes before they happen.

This is a submission draft, not a record of a completed submission. Replace all pending statements with actual verified results before publishing.

## The user and problem

A support operations lead wants to automate refunds but has only a few evaluation cases. An observed success rate says little about rare, expensive mistakes, and “zero failures so far” is often mistaken for safety. RiskGraph makes financial exposure and statistical uncertainty visible while checking proposed actions before execution.

## What we built

RiskGraph pairs a synthetic refund agent with an independent online safety monitor. It evaluates ordinary and adversarial cases, records proposed and executed decisions, and shows how much unauthorized synthetic loss was prevented. A dashboard turns individual decisions into inspectable evidence rather than a single unexplained risk score.

The estimator separates frequency from positive-loss severity. Disclosed Beta and Dirichlet priors keep uncertainty visible when there are few or no failures. A separate conservative time-uniform loss bound supports repeated observation under explicit assumptions. A betting e-process raises a reference-rate alarm as harmful proposals arrive.

## Technology

Python, FastAPI, NumPy/SciPy, SQLite, HTML/CSS/JavaScript, and a Render deployment Blueprint. Claude proposes schema-validated actions through the Anthropic Messages API. SurrealDB Agent Memory is integrated through scoped remember/recall operations so prior incidents can become context for future decisions, without gaining authority over the monitor's policy.

**Verified sponsor use:** the [Render deployment is live](https://riskgraph-fa98.onrender.com). Claude completed separate three-case evaluations with memory off and hosted memory on, with actual API token usage recorded. SurrealDB Agent Memory stored a blocked incident and retrieved it in a later evaluation with source IDs, trace IDs, and typed event extraction; those recalled incidents also reached the Claude decision path. Eon Era is optional and currently not integrated. No Expo or Clerk integration is claimed.

## What is distinctive

The combination of sparse frequency/severity estimates, an independent sequential safety envelope, pre-execution monitoring, and incident provenance helps a reviewer see both what happened and what remains uncertain. We use established mathematics and expose its assumptions; we do not claim a new statistical theorem or production safety from synthetic data.

## Validation

**80 automated tests pass** locally and in GitHub Actions. The deliberately naive 40-case offline fixture produced 26 harmful proposals; the monitor blocked all 26, preventing $2,800 of unauthorized synthetic loss with zero residual loss observed. A separate fresh 20-case Claude evaluation completed with two protocol-invalid escalations blocked and zero unauthorized monetary loss observed. Those escalations carried nonzero amounts but did not propose executing refunds, so they are not counted as prevented financial losses. Separate three-case checks verified Claude alone and Claude with hosted incident recall. These small synthetic samples do not establish a real-world error rate or memory benefit. Raw synthetic exports and the complete validation record are included in the repository. Prevented synthetic loss is not customer savings.

## Limits and next steps

All data and money are synthetic. The workload is deliberately stressful and is not a representative real store. The offline agent is deliberately naive. The monetary cap is $1,000, the severity model rounds upward into bands, and sparse estimates depend on priors. Adaptive-memory runs disable the common-mean sequential bound. Production work needs representative held-out labels, broader harm definitions, user authentication, and operational hardening.

## Prior work and AI disclosure

The project was implemented during Build Week starting October 18, 2026 with AI coding assistance in Codex. No pre-existing RiskGraph source repository or external UI template was provided. Open-source dependencies and established statistical methods are listed in the repository. Team members must add any additional prior work, templates, or AI tools they used.

## Suggested demo, under four minutes

1. Explain the support-lead problem and identify synthetic mode.
2. Run a fixed-seed evaluation and inspect an injection or duplicate-refund decision.
3. Show the independent monitor blocking execution and the audit trail.
4. Compare observed loss, posterior uncertainty, and conservative upper bound; explain why zero observed failures is not zero risk.
5. Show the stored incident and its turn ID, then a later recall trace and a Claude decision supplied with the recalled evidence.
6. Show the actual live Render URL and public GitHub repo, then state limits and the path to production.

## Submission fields still needed

- Public GitHub repository: https://github.com/farzana0/riskgraph
- Successful live deployment: https://riskgraph-fa98.onrender.com
- All team members, up to four.
- Review the included sponsor evidence and measured synthetic results.
- Optional public demo video link, at most four minutes.
