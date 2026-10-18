# Validation record — October 18, 2026

## Automated checks

**47 tests passed** on the final application source in Python 3.9.6. Command: `python -m pytest -q`. Final test duration: 2.29 seconds after dependencies loaded. Dependencies are pinned in the requirements files. Render targets Python 3.11; a remote deployment and container build have not been executed.

After publication, [GitHub Actions also passed on Ubuntu with Python 3.11](https://github.com/farzana0/riskgraph/actions/runs/39147467550), including the tests and 80-case offline evaluation. Initial source commit: `898b7215daac66e15b0b8ee10e1fb304b7cd845f`. Subsequent documentation-only status updates do not change the tested application code.

Coverage includes:

- Strict money validation and monitor checks at policy boundaries.
- A seeded 1,000-case × six-amount policy invariant check: no scored harmful refund passes the monitor.
- Zero-failure uncertainty, prior-only behavior, posterior identities, severity-band rounding, and invalid loss rejection.
- Hoeffding alpha-spending calculation, three sets of 1,500 full simulated trajectories, and e-process behavior.
- Claude tool-request shape, usage, malformed/truncated output, and provider-error redaction using mocked HTTP.
- SurrealDB Agent Memory route, scopes/lens, idempotency, and provenance using mocked HTTP.
- Actual recall content passed into agent decisions; explicit memory-service failures; local memory learning.
- API workflows, cross-origin rejection, operator access, export, replay protection, restart persistence, and missing/invalid inputs.
- Persisted failed-call budget accounting and atomic reservations across separate database connections.

JavaScript syntax check and Python compilation passed. The Blueprint passed **the current official JSON schema** fetched from `https://render.com/schema/render.yaml.json` using jsonschema validation. This verifies configuration structure, not provider account access or a live deployment.

## Reproducible synthetic results

| Run | Seed | Cases | Harmful proposals | Blocked | Synthetic loss prevented | Observed residual loss |
| --- | --- | --- | --- | --- | --- | --- |
| Offline naive fixture, memory off | 42 | 40 | 26 | 26 | $2,800 | $0 |
| Offline fixture, local memory on | 42 | 40 | 21 | 21 | $2,450 | $0 |
| Offline naive fixture, memory off | 42 | 80 | 42 | 42 | $5,775 | $0 |

These are deliberately stressful synthetic workloads and a deliberately naive fixture, not Claude evaluation results. In the memory run, prior injection incidents teach the fixture to escalate later injection cases. Fewer harmful proposals mean less loss needs to be blocked; the lower prevented-loss total is not evidence of a worse monitor. This comparison illustrates the memory path and is not a causal study of hosted SurrealDB Agent Memory.

For the 40-case memory-off demo, posterior proposed mean binned loss is $140.79/decision. With zero observed residual harm, posterior residual mean is still $4.95, and its 95% interval is approximately $0.003–$30.26. The separate conservative residual upper bound is $368.63/decision. Display rounding may show the lower credible endpoint as $0.00; the posterior is not a point mass at zero. Adaptive-memory runs disable the common-mean bound.

Raw 40-case examples are included in `docs/examples/`. Reproduce the 80-case check with `python scripts/evaluate.py --seed 42 --cases 80 --output evidence/offline.json`.

## Browser verification

Manually exercised through the browser:

1. Initial 40-case dashboard renders without browser errors.
2. New evaluation dialog creates and completes a six-case seed-43 run with live progress.
3. Decision trace shows trusted state, the untrusted customer message, proposal, blocking rule, zero execution, and provenance.
4. Full ledger and blocked-only filtering show the correct rows.
5. Evaluation history restores the initial seed-42 run.
6. Methodology and Connections screens display assumptions and unconnected-provider status.
7. Evidence export downloads a JSON file.
8. Desktop 1,440 × 1,000, default narrow viewport, and mobile 390 × 844 layouts were checked. The mobile page has no document-level horizontal overflow; tables scroll within their container.

Dashboard, decision-trace, and mobile screenshots accompany the delivered source archive. The temporary local server is stopped after QA; use the README launch instructions to reopen it.

## Not yet verified

The [Render app](https://riskgraph-fa98.onrender.com) is now live, with verified HTTPS health, dashboard, static assets, synthetic audit/export, and unauthenticated mutation rejection. See `docs/DEPLOYMENT.md` for evidence. Real Anthropic calls, hosted Agent Memory remember/recall, sponsor-credit balances, restart persistence, and Devpost submission are not yet verified. The user reports completing SurrealDB account, promo, and context setup. Eon Era is not integrated. No production-data or real-money operation was attempted.

## Operator-access follow-up

The first attempted live evaluation was rejected by the server's operator check before a run or provider call was created. The original UI only confirmed token storage, which was misleading. A read-only `/api/operator/verify` endpoint now authenticates the entry immediately. The browser trims surrounding whitespace, clears rejected authorization from tab memory, and displays a verified-access message only after the server accepts it. Evaluation-dialog errors are also displayed inside the modal.

The revised suite passes **49 tests**. Added checks verify rejection of missing/wrong tokens, successful authorized access without creating runs or consuming provider attempts, secret redaction, and cross-origin rejection. Browser QA verified an inline evaluation error, immediate invalid-token feedback, and acceptance of the valid local test token with accidental surrounding whitespace. This was a local test credential, not a production credential. The real production operator token still needs to be re-entered and accepted before provider integration tests can proceed.

## Provider diagnostics and evaluation controls

The revised suite passes **60 tests**. New coverage checks HTTP authentication, permission, model/endpoint, credit, rate-limit, timeout, and malformed-output failures; fixed public hints exclude provider response bodies and credentials. A separate test checks that successful memory recall remains recorded when writing fails. API tests confirm a failed Claude call consumes one attempt, adds no observation, and persists a redacted diagnostic.

Browser QA with a mocked authentication failure confirmed that the dashboard shows the actual failed run state and a persistent error, and that **New evaluation** stays available alongside **Continue evaluation**. No live keys or real provider calls were used for that local UI check.

The first deployed Claude check stopped after one failed attempt with zero decisions. The first deployed hosted-memory check completed eight offline-agent decisions: eight recall trace IDs were returned, but all three attempted blocked-incident writes failed. These are partial integration results; neither a successful Claude evaluation nor hosted memory storage is established by them. Error-specific diagnostics are needed before correcting provider settings.

## Sonnet 5.5 compatibility and bounded scope preparation

The deployed retry returned HTTP 400 for Claude; official model-specific documentation identified the unsupported forced-tool setting in our adapter. The corrected request uses `auto`, `strict: true`, a supported schema, and Sonnet 5.5 `between_tools` with low effort. Local validation still rejects invalid bounds, missing tool calls, truncated responses, and wrong tools. A separate memory retry returned HTTP 400 after successful recall. An explicitly missing scope can now be registered with existing `scope:create` authority; the identical fact is retried once with the same idempotency key. Tests reject registration/retry on unrelated 400s, permission errors, rate limits, and server errors, and show that denied registration never changes grants. **70 tests passed** locally. The corrected adapters still require deployed verification.

## Verified hosted memory and private Claude troubleshooting

The deployed revision `ef54a47da3f051b06b2f54665bc17e686b95a2b2` passed health checks. A two-case offline-agent memory run prepared the missing demo scope and stored a blocked incident with a real turn ID. A later two-case run retrieved the incident text, its memory-chunk source ID, an extracted event entity, and recall trace IDs; its new blocked incident was also stored successfully. Claude still returned HTTP 400 with zero observations. The new **72-test** suite checks that redacted provider details appear only in an authenticated operator error response and never in public run/export evidence. Provider keys, the operator token, and provider URLs are removed before that private display. Successful Claude decisions remain pending.

## Workspace-header diagnosis

The authenticated private error from revision `78c90c5` identified the remaining Claude rejection: the configured API key is not workspace-scoped and the request needs `anthropic-workspace-id`. The adapter now supports an explicit `ANTHROPIC_WORKSPACE_ID` and a one-time read-only lookup of the Default workspace with the existing key. **80 tests passed** locally. Tests cover explicit selection, cached Default lookup, denied lookup, archived/invalid/ambiguous/non-default entries, and incomplete pagination. No workspace is created and no permissions are modified. The corrected workspace header still needs deployed verification.
