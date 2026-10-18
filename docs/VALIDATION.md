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
