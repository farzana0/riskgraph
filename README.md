# RiskGraph

**Know the cost before it happens.**

A hackathon MVP for support operations teams evaluating AI refund agents. A synthetic agent proposes refunds, an independent monitor checks trusted order facts before simulated execution, and a dashboard shows frequency/severity risk with honest uncertainty from small samples.

**Live demo:** https://riskgraph-fa98.onrender.com — deployed on Render. Public synthetic evidence is viewable; new evaluations require operator access. See [deployment verification](docs/DEPLOYMENT.md) for completed checks and remaining live-provider validation.

## Try it locally

No Mila cluster, GPU, or account is required for the offline demonstration. Python 3.9–3.11 works; deployment targets Python 3.11.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Open http://127.0.0.1:8765. The first launch creates a 40-case offline evaluation. Choose **New evaluation** to run more cases. Inspect decisions, compare proposed and residual loss, and export JSON evidence. The offline agent is deliberately naive, not a simulated claim about Claude's capabilities.

## Features

- Seeded ordinary, prompt-injection, expired, wrong-owner, duplicate, and high-value refund scenarios.
- Strict money/tool validation; independent ownership, order, window, balance, request, and approval checks.
- Transactional execution ledger, ordered audit events, and replay protection.
- Beta frequency × Dirichlet severity model with 95% posterior intervals and explicit priors.
- Separate time-uniform loss upper bound and e-process reference-rate alarm.
- Actual Claude Messages API and SurrealDB **Agent Memory** remember/recall adapters.
- Responsive dashboard, provenance inspection, evaluation history, and evidence download.
- Persistent Render deployment configuration, container definition, and GitHub Actions checks.

## Architecture and reasoning

See [architecture and implementation plan](docs/ARCHITECTURE.md), [statistical methods](docs/METHODS.md), [verified sources and sponsor requirements](docs/SOURCES.md), and [beginner setup guide](docs/SETUP_GUIDE.md).

```text
seeded case → agent proposal → independent monitor → sandbox ledger
                    ↑                 ↓                 ↓
              prior incidents ← Agent Memory      scored losses
                                                       ↓
                                           risk estimates → dashboard
```

All money and customers are synthetic. Customer text and recalled incidents never authorize refunds. Proposed and residual risk are separate; zero observed residual harm still produces nonzero Bayesian uncertainty. Stationary sequential bounds are disabled for adaptive-memory runs. The dashboard explains assumptions and limitations.

## Connect Claude and Agent Memory

Configure the variable names in `.env.example` as server environment variables. The application does not automatically load a `.env` file. Never commit live keys. Do not expose them in frontend code. Start a new server after changing configuration.

- Claude: set `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, and a long random `RISKGRAPH_ADMIN_TOKEN`. The model default follows the official model list checked October 18, 2026; verify availability in your account before the first run.
- Live API calls require operator access, are limited to 40 cases/run, and reserve against a persisted 200-attempt workspace budget. Failures consume attempts too; there are no automatic retries. These controls are request limits, not a dollar billing guarantee.
- Agent Memory: set `SURREAL_MEMORY_URL` to the HTTPS Context host, `SURREAL_MEMORY_CONTEXT`, and `SURREAL_MEMORY_API_KEY`. Register `SURREAL_MEMORY_SCOPE` (default `org/riskgraph/demo`) first. A generic SurrealDB database endpoint is not an Agent Memory Context.
- In **Connections**, enter the operator token. It stays in tab memory. Start an evaluation with Claude and optionally memory enabled. The token is sent only to your app server, and keys remain server-side.
- Hosted memory errors remain explicit in event evidence; the app does not silently claim a successful sponsor integration. Without a hosted Context, memory runs are labeled `local_demo`.

## Tests and evidence

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python scripts/evaluate.py --seed 42 --cases 80 --output evidence/offline.json
```

Optional real API evaluation, only after configuring the environment:

```sh
.venv/bin/python scripts/evaluate.py --mode claude --seed 901 --cases 20 --output evidence/claude-heldout.json
```

The CLI and server share the configured database's attempt budget. Keep training/memory and held-out evaluation seeds separate. Export actual live results before credit expiry. Local fixtures and mocked contract tests do not verify account access.

## Deploy

Publish these source files at the root of a GitHub repository. In Render create a Blueprint from `render.yaml`, redeem the Build North credit first, and review costs. It defines one small paid web service and persistent disk. Optional provider environment values can be left unset until ready; never set only part of the Agent Memory trio. Add real values from Render's Environment page when connecting providers. Render generates the operator token.

Use a single worker/instance. The SQLite disk persists runs and live-attempt counters across restart; disk backup and production disaster recovery are outside this MVP. Public GET endpoints expose synthetic audit evidence only. Anyone visiting can inspect the demo, while operator access protects mutations on Render. The operator token is an internal demo control, not user authentication; no Clerk integration or category claim is made.

Verify `/healthz`, the dashboard, a new run with the operator token, export, a blocked injection trace, and persistence after a restart. The exact URL must come from a successful Render deployment, not this README. See [setup guide](docs/SETUP_GUIDE.md).

## Build North disclosure

Prepared during Build Week starting October 18, 2026, with AI coding assistance in Codex. Architecture, statistical choices, application code, UI, synthetic scenarios, tests, and deployment scaffolding were prepared in this chat. No pre-existing RiskGraph repository was provided. Established mathematical methods and third-party libraries are credited in `docs/METHODS.md` and `docs/SOURCES.md`. No external UI template or third-party customer dataset was used. Participants must review this disclosure and add any other work or tools they used before submission.

**Current delivery boundary:** the offline MVP and contract-tested adapters are published at [farzana0/riskgraph](https://github.com/farzana0/riskgraph), and the [Render demo is live](https://riskgraph-fa98.onrender.com). [GitHub's automated checks passed](https://github.com/farzana0/riskgraph/actions/runs/39147467550). Both provider configurations are detected by the deployed app. Real Claude calls, hosted Agent Memory read/write verification, a persistence restart check, and Devpost submission are still pending.
