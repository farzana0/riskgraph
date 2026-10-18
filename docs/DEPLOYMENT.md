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

## Verified provider integrations

Both provider configurations have been exercised, rather than inferred from environment-variable presence. The participant privately set `ANTHROPIC_WORKSPACE_ID`; the app now reports explicit selection and sends the workspace header with its existing API key.

- Claude, seed 901, memory off: 3/3 completed decisions, 2,459 input / 683 output tokens.
- Claude, seed 902, hosted memory on: 3/3 completed decisions, 3,611 input / 782 output tokens, actual recalled hits and trace IDs.
- Fresh Claude evaluation, seed 20261018, memory off: 20/20 completed, 16,435 input / 4,911 output tokens. The monitor blocked two nonzero-amount escalations; zero unauthorized monetary loss was observed. These were protocol inconsistencies, not prevented refund losses.
- Hosted memory write: run `dd7a8fa481334ae0872e699cc6bc247d` prepared the missing demo scope with existing authority and stored a blocked incident with turn ID `kb0vqkk8tmy7nnu09bc7`.
- Later hosted recall: run `5bb6d0f7e5e84aa08c9e4b541c57003b` retrieved that incident as `memory_chunk:sreu9hdaeqnkgvubby3v` with an extracted event entity and trace IDs, then stored another incident.

Application revision `540d8c86674d0ea1b48ac118fd6cd3a9417f6862` is live and passed 80 automated tests. Public synthetic exports are in `docs/examples/`; see `docs/VALIDATION.md` for assumptions and limits. Five earlier rejected Claude requests produced no observations and remain included in the persisted 31-attempt counter. Private provider diagnostics are returned only to the authenticated operator and excluded from public evidence.

The Blueprint declares a 1 GB disk mounted at `/var/data` and SQLite at `/var/data/riskgraph.sqlite3`. After the operator-verification update was deployed, the original evaluation `4b986541db4d4808af699ceac169dd33` was still present. This verifies evaluation persistence across that code redeploy. The disk's dashboard settings and disaster recovery have not been independently inspected.

The deployed access update exposes `POST /api/operator/verify`: a request without a token returns HTTP 401, and the dashboard now shows **Verify operator access**. Operator access was verified in the agent preview, and the actual provider evaluations above were completed there. Access stays in the verified tab; a separate tab must verify independently before mutating evaluations.

No real payments, real customer data, Eon Era evaluation, or Devpost submission have been performed. The configured-provider checks are public booleans only; no secret values were retrieved.

## Verification follow-up

The participant suggested ideas inspired by Lean and agent verification. The current monitor already implements explicit policy checks before execution, with boundary and invariant tests. It is not a proof of correctness for the full AI agent. A bounded next step is independently checked authorization evidence per decision and arithmetic policy-model verification, with a clear distinction between model proofs and tested Python implementation. Deployment and working provider integrations take priority over adding a theorem prover.
