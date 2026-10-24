# RiskGraph

**[Open RiskGraph](https://riskgraph-fa98.onrender.com).** Follow one clear step per page: [discover candidate failures](https://riskgraph-fa98.onrender.com/discover), [import private trace evidence](https://riskgraph-fa98.onrender.com/evidence), [inspect an agent decision](https://riskgraph-fa98.onrender.com/challenge), [compare safeguards](https://riskgraph-fa98.onrender.com/compare), and [project loss-tail risk](https://riskgraph-fa98.onrender.com/risk).

The latest [record-grounded replication](docs/TRAVEL_V3.md) compares the original and revised workflows on **32 fresh harder trips across 16 model/memory/critic configurations**. Both models use the same output schema, adaptive thinking, low effort and 1,536-token allowance. The study completed 503 real requests plus ten discovery requests for **US$4.8499**. The revised package removes the observed adjudicated errors on this batch, with two initial Haiku/no-memory responses still unresolved; incremental memory and critic benefits remain uncertain. A separate small development pass enumerates candidate failures with source citations; its suggestions never count as held-out incidents. [Private trace format and explicit source-transfer assumptions](docs/TRACE_EVIDENCE.md).

The prior [matched travel comparison](docs/TRAVEL_FACTORIAL.md) contains 32 identical trips across eight configurations and 256 real requests, costing US$1.9156. Its [mistake audit](docs/examples/travel-error-audit.json) identifies unnecessary escalations and deadline-reading errors rather than a general model ranking. All earlier archives remain separate and immutable.

The preceding registered experiments contain **6,012 real model requests**: a fresh 48-case refund replication (381 requests), a matched 32-case travel study (127), and 5,504 fresh format-controlled Haiku travel cases. Estimated study token cost is **US$7.4663**. An additional offline campaign tests 6,000 injected failures and 6,000 valid controls. These sources remain separate. Live discretionary reviews and replay never enter the registered risk estimates.

Inspect quote/ledger records, initial decisions, separate Sonnet corrections, and independent gate outcomes. The large Haiku study exposes 2,247 harmful adjudicated proposals and 721 unresolved proposals; its response controls differ from the matched study and cannot support a pooled model ranking. Its conditional positive-loss credible interval narrows about 90% from the 32-case prefix to the full batch. Conservative bounds and missing outcomes remain explicit. [Fresh memory/critic results](docs/FRESH_FOLLOWUP.md) · [Travel model comparison](docs/TRAVEL_DEMO.md) · [Large tail-probability study](docs/TRAVEL_SCALE.md) · [Calibration limits](docs/TAIL_CALIBRATION.md).

The earlier [36-case memory investigation](https://riskgraph-fa98.onrender.com/study?experiment=memory-v3) and [48-case development study](https://riskgraph-fa98.onrender.com/study?experiment=original) remain available without pooling.

**[Interactive agent topology demo](https://riskgraph-fa98.onrender.com/demo).** Inspect saved agent decisions through four monitoring setups, then explore a separate Beta–Binomial frequency model, editable traffic assumptions, and fixed-sample exact upper bounds. Start locally with `./scripts/start-demo.sh` and open `http://127.0.0.1:8765/demo`. [Design, assumptions, and three-minute demo script](docs/PAIRED_DEMO.md). [Paired statistical model and calibration audit](docs/MODEL_AUDIT.md).

Assess reviewed agent outcomes, separate proposed exposure from executed loss, and quantify uncertainty at the business-episode level. The [assessment workspace](https://riskgraph-fa98.onrender.com/workspace) accepts JSON/JSONL or a synthetic example; numeric analysis is stateless. The evaluation lab contains reproducible refund-agent scenarios and optional paired model reviews.

Research specification: [methods, authority model, experiments and limitations](docs/RESEARCH_DESIGN.md). Framework choice: [Hermes, OpenClaw and openJiuwen](docs/FRAMEWORK_DECISION.md). The current runtime is a framework-neutral typed workflow; none of those SDKs is embedded.

**Risk monitoring for AI refund agents.**

RiskGraph evaluates refund proposals through a proposal–review–execution workflow and measures monetary exposure from small samples. Independent policy checks gate simulated execution. The dashboard distinguishes observed loss, time-uniform confidence bounds, Bayesian estimates, and incident provenance.

[Live application](https://riskgraph-fa98.onrender.com) · [Source repository](https://github.com/farzana0/riskgraph) · [Validation record](docs/VALIDATION.md)

## Research evidence

- [Matched Haiku–Sonnet comparison](docs/PAIRED_MODELS.md): 320 real-model cases, explicit uncertainty and no unsupported superiority claim.
- [Adaptive financial monitoring study](docs/ASSURANCE_RESULTS.md): 50,000 trajectories and 25 million observations.
- [Symbolic gate verification](docs/POLICY_VERIFICATION.md): solver-checked policy predicates, six negative controls and a reproducible SMT-LIB query.
- [Execution and coordination scenarios](docs/OPERATIONAL_SCENARIOS.md): settlement faults, common dependencies and unresolved outcomes.

## Capabilities

- Thirteen reproducible suites, including 28 explicit identity, manipulation, payment, and combined-failure scenarios.
- Strict action schemas and independent ownership, order, refund-window, balance, request, and approval checks.
- Transactional execution ledger, ordered audit events, and replay protection.
- Beta frequency × Dirichlet severity estimates with 95% posterior intervals and explicit priors.
- Beta-mixture loss-tail confidence sequences with a shared risk error budget.
- A multi-rate, precommitted restart-mixture alarm for conditional harm exceedance.
- Read-only policy reviews, fail-closed consistency checks, and recomputable evidence.
- Claude Messages API proposals and SurrealDB Agent Memory incident storage and retrieval.
- A plain-language risk review with consistent icons, observed outcomes, conservative exposure estimates, searchable decisions, and optional statistical detail.
- A validation view comparing current and earlier methods on recorded simulations.
- Render deployment configuration, persistent storage, and automated checks.

All public demo customers, orders, messages, and monetary outcomes are synthetic. Operator-imported observations stay private and retain their source. The offline agent is a deliberately naive test fixture. Its results demonstrate policy enforcement; Claude performance is recorded in separate API evaluations.

## Local development

Python 3.9–3.11 is supported; deployment targets Python 3.11. The offline evaluation runs on a standard CPU without external services.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Open http://127.0.0.1:8765 and choose a demo, evidence, or log assessment. The evaluation lab is under `/workspace`. On first launch, the application creates a 40-case offline evaluation. **New evaluation** creates a separate run; **Continue evaluation** resumes an unfinished run. The decision ledger provides policy checks, simulated outcomes, and exports.

## Architecture

```text
scenario suite → agent proposal → policy review → execution gate → sandbox ledger
                     ↑                ↑                ↓                ↓
                     └──── incident memory ───── blocked evidence    scored loss
                                                                        ↓
                                              confidence bounds + estimates + alarm
```

Customer messages and recalled incidents provide context, never authorization. The independent monitor gates execution; disagreements with the deterministic reviewer pause the evaluation. Proposed and residual losses are scored separately. Zero observed harm retains uncertainty. Adaptive-memory, designed catalogue, drift, and correlated suites disable stationary confidence bounds.

See [system architecture](docs/ARCHITECTURE.md), [statistical methods](docs/METHODS.md), [configuration guide](docs/SETUP_GUIDE.md), and [technical references](docs/SOURCES.md).

## Provider configuration

Server environment variables are documented in [.env.example](.env.example). Environment changes require a server restart; the application does not automatically load `.env` files. Credentials remain server-side and outside version control.

- **Claude:** `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, and `RISKGRAPH_ADMIN_TOKEN`. Multi-workspace keys can select a workspace through `ANTHROPIC_WORKSPACE_ID`; otherwise the adapter attempts one read-only lookup for a unique active Default workspace.
- **Agent Memory:** `SURREAL_MEMORY_URL` (HTTPS Context host), `SURREAL_MEMORY_CONTEXT`, `SURREAL_MEMORY_API_KEY`, and `SURREAL_MEMORY_SCOPE`. A Context endpoint is required; a generic database endpoint is insufficient.
- **Operator access:** verify the configured operator token in **Connections** before creating or advancing protected evaluations. The token is retained only in the current tab.

Claude evaluations allow up to 40 cases per run and reserve against a persisted 500-attempt budget by default, including failed calls. Token usage is recorded. Hosted-memory errors appear explicitly in event evidence; local memory is labeled `local_demo`.

## Validation

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python scripts/evaluate.py --seed 42 --cases 80 --output evidence/offline.json
```

With provider credentials configured, an API evaluation can be run with:

```sh
.venv/bin/python scripts/evaluate.py --mode claude --seed 20261018 --cases 20 --output evidence/claude-evaluation.json
```

The CLI and server share the configured database's attempt budget. Evaluation seeds and settings are recorded for reproducibility. Development and memory-training seeds should remain separate from held-out evaluation seeds.

The validation suite contains 211 tests. An earlier revised-workflow campaign completed 136 hosted Claude decisions, including 68 with actual SurrealDB retrieval traces; all reviews recomputed successfully, with no observed harmful proposal, protocol rejection, or residual loss. A subsequent paired comparison adds 320 Haiku/Sonnet cases; both models record zero harmful proposals on this workload. Historical provider checks remain separate. The [expanded failure campaign](docs/FAILURE_SCENARIOS.md) adds 100,000 policy proposals, 2,856 workflow decisions, and operational fault injection. Raw evidence is available in [docs/examples](docs/examples).

The [featured control demonstration](docs/CONTROL_DEMO.md) includes $6,914.98 in unauthorized proposed payments across 56 decisions. All 48 harmful proposals are blocked; eight valid payments execute. Injected failures are explicitly separated from real Claude evaluations.

## Simulation study

The [mathematical framework comparison](docs/FRAMEWORK_V2.md) includes 50,000 policy-stress proposals, 3,440 workflow decisions, and 120,000 monitoring trajectories. At a 15% harm rate, the mixture alarm detected 80.19% of trajectories within 500 cases, compared with 17.34% for the original alarm. The current null false-alarm rate was 2.31% in the recorded simulation. No sampled harmful proposal bypassed the policy checks.

```sh
.venv/bin/python scripts/evaluate.py --suite adversarial --seed 21031 --cases 40 --output evidence/adversarial.json
.venv/bin/python scripts/evaluate_v2.py --output evidence/framework-v2.json
.venv/bin/python scripts/stress_campaign.py --output evidence/failure-campaign.json
```

The [monitoring stress study](docs/MONITORING_STRESS.md) adds 100,000 trajectories across ten failure patterns, including severity-only shifts and rare catastrophic errors that a frequency alarm need not detect.

The [original study](docs/SIMULATIONS.md) remains available as historical evidence, including workload-dependent Bayesian interval coverage. Current bounds and alarm guarantees are derived in [METHODS.md](docs/METHODS.md). Synthetic measurements do not establish production safety or a causal Claude memory benefit.

## Deployment

The [Render deployment guide](docs/DEPLOYMENT.md) describes the Blueprint, persistent disk, environment variables, and release checks. The service runs one Python worker with SQLite on a persistent disk. Public read endpoints expose synthetic evidence; an operator token protects mutations. Production deployment requires additional identity, isolation, and recovery controls.

## Development attribution

RiskGraph was developed for Build North 2026 with AI coding assistance from Codex and Claude. The topology interface and editable SVG design assets were supplied through a Claude design handoff and integrated with the tested backend. Statistical methods and third-party dependencies are credited in [methods](docs/METHODS.md) and [references](docs/SOURCES.md). The interface and synthetic scenarios are project-specific; no external UI template or customer dataset is used.


## Harder real-model comparison

Open **Stress tests → Does a second agent actually help?** to compare both models with memory and corrective critic independently on or off. The [32-case primary study and 16-case higher-response follow-up](docs/HARD_BENCHMARK.md) contain genuine unsafe proposals, service errors, critic corrections and regressions. All data and money are synthetic; model outputs and SurrealDB retrieval are real. The follow-up completed all configurations without truncation. The website shows uncertainty, raw mistakes and the evolution of the risk estimate; these challenge sets do not identify a production failure rate.
