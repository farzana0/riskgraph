# Verified sources and sponsor status

Checked October 18, 2026. Public documentation verification is distinct from account/credit verification.

| Source | Verified use and implication |
| --- | --- |
| [Build North requirements](https://build-north.devpost.com/) | Submit by Oct 25 at 11:59 p.m. ET with public GitHub source, write-up, team, prior-work disclosure, and live link where applicable. Video is optional, ≤4 minutes. Partner awards require genuine platform use. SurrealDB category specifies Agent Memory; Eon specifies Era. Top teams demo Oct 29 in Toronto. |
| [GitHub repository creation](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository) | Verified public repository creation and leaving initialization options unset for an existing prepared project. |
| [Detailed rules](https://build-north.devpost.com/rules) | Age 18+, Canada residence, teams ≤4, one submission. Build during Build Week and disclose AI tools/templates/prior work. Public code and demo; no misuse of private data. These detailed eligibility rules are narrower than the overview's generic summary. |
| [Sponsor resources](https://build-north.devpost.com/resources) | Render $50 via linked form; SurrealDB $50 Agent Memory credit with code BUILDNORTH50; Era early access. These public offers are not proof that the participant's accounts have received them. |
| [Render credits](https://render.com/docs/credits) | Review actual balance, applicability, and expiration in the account. This project has not redeemed credits or accepted billing terms. |
| [Render Blueprint reference](https://render.com/docs/blueprint-spec) | Current Python web-service configuration, disk, health path, generated secret, and current `0.5c-512mb` plan identifier. Actual deployment not yet verified. |
| [Render FastAPI guide](https://render.com/docs/deploy-fastapi) | Server starts with Uvicorn bound to host 0.0.0.0 and Render's PORT. |
| [Render first deploy](https://render.com/docs/your-first-deploy) | Requires code repository/Git provider and a service; account access is not available in this session. |
| [Anthropic models](https://platform.claude.com/docs/en/models/overview) | Default model ID `claude-sonnet-5-5` from the current official model table. Account availability must be checked before live calls. Model is configurable. |
| [Claude tool definition](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools) | Client tool with `input_schema` and forced tool selection; output is validated locally before monitoring. This project uses tools, not an invented text-to-JSON guarantee. |
| [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing) | Current standard Sonnet 5.5 rates listed as $2/input million tokens and $10/output million tokens; the app records usage rather than pretending to know the organisation's remaining dollar credit. |
| [Agent Memory reference](https://surrealdb.com/docs/agent-memory/reference/rest-api) | Context-host routes `/api/v1/{context_id}/facts` and `/query`; Bearer Context key. Writes use `scopes`, reads use `lens`, with explicit nested scope selectors. Write idempotency uses event IDs. Trace and turn identifiers retained. |
| [Agent Memory hosted quickstart](https://surrealdb.com/docs/agent-memory/quickstarts/hosted) | Provision Context and key in Studio; register scope before use. Generic SurrealDB CRUD alone does not establish this integration. |
| [SurrealDB sponsor resource pack](https://surrealdb.notion.site/Build-North-SurrealDB-participant-resources-pack-3edbfa44ae3e81a0a6ebd0b4fbb802d3) | Initial public fetch returned 404. The participant subsequently supplied the full pack in chat: prize emphasis includes typed/time-aware facts, supersession, source-traceable retrieval, and coherent shared memory across more than one agent. The current MVP has incident remember/recall; policy supersession and a second application agent are next-stage work, not completed features. |
| [Eon Era announcement](https://www.eon.io/blog/era-build-and-test-ai-agents) | Realistic synthetic companies and simulated enterprise APIs/MCP for benchmarking; optional and unimplemented in this MVP. Linked organiser Drive setup guide could not be fetched. |
| [Howard et al. confidence sequences](https://arxiv.org/abs/1810.08240) | Primary research background for time-uniform inference. This implementation uses a simpler Hoeffding union-bound construction with its own derivation. |

## Supplied conversation evidence

The earlier conversation's two text attachments contained Build North Discord announcements. They describe Anthropic $100 credits, application deadlines, and reported activation/error issues; they are historical participant-supplied material. The user states their credits expire October 21. Neither the current balance nor that account-specific expiry has been verified by signing into the console.

The attachments also mention Eon office hours October 19 at 1–1:30 p.m. ET and SurrealDB October 21 at noon–12:30 p.m. ET. Treat those as copied announcements; check the current Discord event before attending. No calendar event or reminder has been created.

## Evidence boundaries

The source is now published at https://github.com/farzana0/riskgraph (initial source commit 898b7215daac66e15b0b8ee10e1fb304b7cd845f), and [GitHub Actions passed](https://github.com/farzana0/riskgraph/actions/runs/39147467550). The participant reports creating the SurrealDB account, redeeming the promo, and completing Agent Memory context setup; account balances and the context have not been independently inspected. No live provider keys were present in the execution environment. Live API calls, hosted memory operations, Render deployment, and Devpost submission remain unverified.
