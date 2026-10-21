# Render deployment

[Live application](https://riskgraph-fa98.onrender.com) · [Source repository](https://github.com/farzana0/riskgraph)

## Service configuration

The root `render.yaml` defines one Python web service, a generated operator token, and a persistent evidence disk.

| Setting | Value |
| --- | --- |
| Runtime | Python 3.11 |
| Compute | `0.5c-512mb` |
| Build | `pip install -r requirements.txt` |
| Start | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1` |
| Health check | `/healthz` |
| Disk | 1 GB mounted at `/var/data` |
| Database | `/var/data/riskgraph.sqlite3` |

A single worker and instance preserve the SQLite orchestration model. Source files must be at the repository root. Setup steps and provider variables are documented in [SETUP_GUIDE.md](SETUP_GUIDE.md).

## Environment and access

Provider credentials are stored in Render's service environment. Environment changes take effect after a successful deployment. `ANTHROPIC_WORKSPACE_ID` selects the intended Claude workspace for multi-workspace keys. The Agent Memory host, Context ID, and API key form a complete configuration.

Public read endpoints expose synthetic evaluations and exports. Evaluation mutations require the configured operator token and pass same-origin checks. **Connections → Verify operator access** validates the token without making provider calls or creating an evaluation. Access is held in the current tab only. Private provider diagnostics are restricted to authenticated error responses and excluded from public exports.

## Release checks

1. Confirm the Render deployment is **Live** and `/healthz` reports the intended source revision.
2. Load the overview, decision ledger, methodology, and Connections views.
3. Confirm JavaScript and CSS load successfully and the evaluation history is available.
4. Verify an unauthenticated mutation returns HTTP 401 without creating a run.
5. With operator access, complete a small evaluation from a new scenario suite, inspect its policy review, verify decision evidence, and download its JSON export.
6. Verify new and historical evaluations remain available after a redeploy. Historical events without review records must remain labeled legacy.
7. When provider configuration changes, complete a small API check and inspect memory write/recall evidence as applicable.

Provider calls consume the configured attempt budget. Interface-only releases can be checked without new paid API calls. Framework releases should distinguish local simulation evidence from fresh provider checks. Release v0.2 reports health version `0.2.0`; the deployed source revision identifies the active release.

## Recorded integration evidence

The October 18, 2026 validation includes:

- Health, dashboard, assets, configuration, export, and unauthenticated mutation checks.
- A 40-case offline evaluation with 26 harmful proposals blocked, $2,800 of synthetic loss prevented, and zero observed residual loss.
- Two three-case Claude API checks, with memory off and hosted memory on.
- A fresh 20-case Claude evaluation with two protocol-invalid escalations blocked and zero unauthorized monetary loss observed. The blocked escalations were not refund attempts and are not counted as prevented financial loss.
- Hosted Agent Memory storage and later retrieval with source, turn, and trace identifiers.
- Original evaluation records retained across multiple code and environment redeploys.

The complete results, tested revision, and raw exports are documented in [VALIDATION.md](VALIDATION.md) and [examples](examples). Integration checks establish the tested workflow; representative production performance and disaster recovery require separate validation.
