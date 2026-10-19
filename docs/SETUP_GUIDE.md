# Configuration guide

RiskGraph runs locally as a Python application and deploys to Render through a repository Blueprint. Claude and SurrealDB Agent Memory are optional provider integrations; offline evaluations work without external services.

## Local application

1. Install Python 3.9–3.11; Python 3.11 is the deployment target.
2. Create a virtual environment and install `requirements.txt` as described in the [README](../README.md).
3. Start `uvicorn app.main:app --host 127.0.0.1 --port 8765` from the repository root.
4. Open http://127.0.0.1:8765 and inspect the initial 40-case synthetic evaluation.

Configuration is read from the server environment. The application does not automatically load `.env` files. [.env.example](../.env.example) lists the supported variables. Credential values belong in a local environment manager or hosting secret store, outside version control and public evidence.

## Claude

1. Create an API key in [Claude Console](https://platform.claude.com/) with access to the configured model.
2. Set `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` on the server.
3. Set a long random `RISKGRAPH_ADMIN_TOKEN` to enable protected API evaluations.
4. For a multi-workspace key, set `ANTHROPIC_WORKSPACE_ID` to the intended workspace's `wrkspc_…` ID from **Settings → Workspaces**. Without an explicit ID, the adapter attempts one read-only Default-workspace lookup.
5. Restart or redeploy after environment changes.
6. In the application, open **Connections**, enter the operator token, and choose **Verify operator access**.
7. Start a small **Claude · real API evaluation**, inspect the decision traces and token usage, then export the evidence.

Each case makes one model request. The application limits live runs to 40 cases and reserves against a persisted attempt budget, including failed calls. Provider-side spending controls are separate from this request limit.

## SurrealDB Agent Memory

1. In [SurrealDB Studio](https://studio.surrealdb.com/), open **Agent Memory → Deploy new context** and create a Context.
2. Copy the Context host and Context ID from its connection details. The host is an HTTPS URL; the Context ID is distinct from its display name.
3. Create a scoped API key and register the intended scope, default `org/riskgraph/demo`.
4. Configure the server variables below as a complete set.
5. Restart or redeploy, enable **Recall prior incidents before decisions**, and inspect memory provenance in the decision trace.

| Variable | Value |
| --- | --- |
| `SURREAL_MEMORY_URL` | HTTPS Agent Memory Context host, without `/api/v1/...` |
| `SURREAL_MEMORY_CONTEXT` | Context ID |
| `SURREAL_MEMORY_API_KEY` | Context API key with the required scope permissions |
| `SURREAL_MEMORY_SCOPE` | Registered scope path |

A generic SurrealDB database endpoint cannot substitute for an Agent Memory Context. With a configured Context, provider failures are recorded explicitly. Without one, memory evaluations use labeled local demonstration memory. Successful storage and a later recall with source/trace identifiers provide integration evidence.

## Render

1. Place the source files at the root of a GitHub repository, including `render.yaml`, `requirements.txt`, and `app/`.
2. In Render, create a **Blueprint** connected to that repository and select `render.yaml`.
3. Review the service and persistent-disk configuration, then create the service.
4. Configure optional provider values under the service's **Environment** page. Keep the Agent Memory host, Context ID, and key either fully configured or all unset.
5. Render generates `RISKGRAPH_ADMIN_TOKEN`. Authorized operators use that value in **Connections**; it is retained only in the current application tab.
6. After deployment is **Live**, follow the release checks in [DEPLOYMENT.md](DEPLOYMENT.md).

Saving environment changes requires a deployment before they take effect. If a source update has not deployed automatically, use **Manual Deploy → Deploy latest commit**. The live `/healthz` response reports the deployed source revision.

## Evaluation workflow

1. Select **New evaluation** and choose the agent, case count, seed, and memory mode.
2. Start the run; **Continue evaluation** resumes unfinished cases.
3. Inspect monitor verdicts and proposed versus residual loss in the ledger.
4. Review uncertainty intervals and their assumptions under **Risk methodology**.
5. Export JSON evidence before changing evaluation settings. New models, prompts, or policies require a separate run.

The [validation record](VALIDATION.md) distinguishes offline fixtures, API evaluations, hosted-memory evidence, and production limitations.
