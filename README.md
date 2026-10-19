# RiskGraph

**Risk monitoring for AI refund agents.**

RiskGraph evaluates refund proposals before simulated execution and estimates monetary exposure from small samples. An independent policy monitor checks trusted order facts, while the dashboard reports proposed risk, residual risk, uncertainty intervals, and incident provenance.

[Live application](https://riskgraph-fa98.onrender.com) · [Source repository](https://github.com/farzana0/riskgraph) · [Validation record](docs/VALIDATION.md)

## Capabilities

- Reproducible ordinary, prompt-injection, expired, wrong-owner, duplicate, and high-value scenarios.
- Strict action schemas and independent ownership, order, refund-window, balance, request, and approval checks.
- Transactional execution ledger, ordered audit events, and replay protection.
- Beta frequency × Dirichlet severity estimates with 95% posterior intervals and explicit priors.
- Separate time-uniform loss upper bounds and a sequential reference-rate alarm.
- Claude Messages API proposals and SurrealDB Agent Memory incident storage and retrieval.
- Evaluation history, decision traces, memory provenance, and JSON evidence exports.
- Render deployment configuration, persistent storage, and automated checks.

All customers, orders, messages, and monetary outcomes are synthetic. The offline agent is a deliberately naive test fixture. Its results demonstrate policy enforcement; Claude performance is recorded in separate API evaluations.

## Local development

Python 3.9–3.11 is supported; deployment targets Python 3.11. The offline evaluation runs on a standard CPU without external services.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Open http://127.0.0.1:8765. On first launch, the application creates a 40-case offline evaluation. **New evaluation** creates a separate run; **Continue evaluation** resumes an unfinished run. The decision ledger provides policy checks, simulated outcomes, and exports.

## Architecture

```text
seeded case → agent proposal → independent monitor → sandbox ledger
                    ↑                 ↓                 ↓
              prior incidents ← Agent Memory      scored losses
                                                       ↓
                                           risk estimates → dashboard
```

Customer messages and recalled incidents provide context, never authorization. Only the independent monitor can allow a simulated refund. Proposed and residual losses are scored separately. Zero observed residual harm retains nonzero posterior uncertainty; adaptive-memory runs disable the stationary sequential bound.

See [system architecture](docs/ARCHITECTURE.md), [statistical methods](docs/METHODS.md), [configuration guide](docs/SETUP_GUIDE.md), and [technical references](docs/SOURCES.md).

## Provider configuration

Server environment variables are documented in [.env.example](.env.example). Environment changes require a server restart; the application does not automatically load `.env` files. Credentials remain server-side and outside version control.

- **Claude:** `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, and `RISKGRAPH_ADMIN_TOKEN`. Multi-workspace keys can select a workspace through `ANTHROPIC_WORKSPACE_ID`; otherwise the adapter attempts one read-only lookup for a unique active Default workspace.
- **Agent Memory:** `SURREAL_MEMORY_URL` (HTTPS Context host), `SURREAL_MEMORY_CONTEXT`, `SURREAL_MEMORY_API_KEY`, and `SURREAL_MEMORY_SCOPE`. A Context endpoint is required; a generic database endpoint is insufficient.
- **Operator access:** verify the configured operator token in **Connections** before creating or advancing protected evaluations. The token is retained only in the current tab.

Claude evaluations allow up to 40 cases per run and reserve against a persisted 200-attempt budget by default, including failed calls. Token usage is recorded. Hosted-memory errors appear explicitly in event evidence; local memory is labeled `local_demo`.

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

The validation suite contains 80 tests. Recorded API checks include 26 completed Claude decisions across three runs and successful hosted-memory storage and later retrieval. The fresh 20-case Claude evaluation blocked two protocol-invalid escalations and observed zero unauthorized monetary loss. These synthetic samples establish integration behavior, not production safety. Raw evidence is available in [docs/examples](docs/examples).

## Deployment

The [Render deployment guide](docs/DEPLOYMENT.md) describes the Blueprint, persistent disk, environment variables, and release checks. The service runs one Python worker with SQLite on a persistent disk. Public read endpoints expose synthetic evidence; an operator token protects mutations. Production deployment requires additional identity, isolation, and recovery controls.

## Development attribution

RiskGraph was developed for Build North 2026 with AI coding assistance from Codex. Statistical methods and third-party dependencies are credited in [methods](docs/METHODS.md) and [references](docs/SOURCES.md). The interface and synthetic scenarios are project-specific; no external UI template or customer dataset is used.
