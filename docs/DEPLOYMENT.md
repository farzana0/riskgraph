# Render deployment — October 18, 2026

Live application: https://riskgraph-fa98.onrender.com

Source: https://github.com/farzana0/riskgraph

Participant-provided Render identifiers:

- Blueprint: `exs-dbag4oe1egvs73aj8h70`
- Web service: `srv-dbag84jncjis73dfd580`
- Initial deployed source: `637774c7e36dc035840f3eda4f5f830b8326e53e`

## Verified public smoke checks

Direct HTTPS checks returned:

| Check | Result |
| --- | --- |
| `/healthz` | HTTP 200, status ok, app version 0.1.0 |
| Dashboard `/` | HTTP 200, RiskGraph UI present |
| JavaScript and CSS | Both HTTP 200 |
| `/api/config` | HTTP 200; both providers configured; operator access required |
| Initial evaluation | 40 completed synthetic decisions, 26 harmful proposals and 26 blocked |
| Prevented synthetic loss | $2,800; observed residual harm $0 |
| Evidence export | HTTP 200 with downloadable JSON filename |
| Mutation without operator token | HTTP 401; no evaluation created |
| Browser rendering | Deployed dashboard and Connections screen rendered correctly |

The configured Claude model is `claude-sonnet-5-5`. The persisted workspace attempt budget is 200 calls; zero attempts had been used at the first deployment check.

## Remaining integration checks

Configured environment variables are not proof that credentials or endpoints work. The first actual Claude request failed without producing a decision. An eight-case hosted-memory run returned recall trace IDs for every case, but all three blocked-incident writes failed. Safe provider diagnostics are being deployed to identify the required correction; successful Claude decisions and memory storage remain unverified. The operator token is entered privately in the app's Connections screen; it must not be copied into chat or committed to source. A successful memory test must retain actual recall trace and memory turn identifiers. The participant's `quick-dragon` resource name has not yet established whether it is an Agent Memory Context or a generic database instance.

The Blueprint declares a 1 GB disk mounted at `/var/data` and SQLite at `/var/data/riskgraph.sqlite3`. After the operator-verification update was deployed, the original evaluation `4b986541db4d4808af699ceac169dd33` was still present. This verifies evaluation persistence across that code redeploy. The disk's dashboard settings and disaster recovery have not been independently inspected.

The deployed access update exposes `POST /api/operator/verify`: a request without a token returns HTTP 401, and the dashboard now shows **Verify operator access**. The participant reports successful verification in their own browser tab. Access is held only in that tab; an agent preview is a separate session. Actual provider calls still require starting an evaluation from the verified tab.

No real payments, real customer data, Eon Era evaluation, or Devpost submission have been performed. The configured-provider checks are public booleans only; no secret values were retrieved.

## Verification follow-up

The participant suggested ideas inspired by Lean and agent verification. The current monitor already implements explicit policy checks before execution, with boundary and invariant tests. It is not a proof of correctness for the full AI agent. A bounded next step is independently checked authorization evidence per decision and arithmetic policy-model verification, with a clear distinction between model proofs and tested Python implementation. Deployment and working provider integrations take priority over adding a theorem prover.
