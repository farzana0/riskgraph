# Technical references

Documentation reviewed October 18, 2026. Integration evidence is recorded separately in [VALIDATION.md](VALIDATION.md).

## Platform documentation

| Source | Application |
| --- | --- |
| [Render Blueprint reference](https://render.com/docs/blueprint-spec) | Python web-service configuration, disk, health path, generated secret, and `0.5c-512mb` plan identifier |
| [Render FastAPI guide](https://render.com/docs/deploy-fastapi) | Uvicorn bound to `0.0.0.0` and Render's `PORT` |
| [Render deployment guide](https://render.com/docs/your-first-deploy) | Repository-based service creation and deployment |
| [Anthropic models](https://platform.claude.com/docs/en/models/overview) | Configurable model selection; current default `claude-sonnet-5-5` |
| [Sonnet 5.5 migration](https://platform.claude.com/docs/en/models/sonnet-5-5/migration-guide) | Automatic tool selection and `between_tools` compatibility |
| [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) | Strict remote tool schema; unsupported numerical/string bounds enforced by the complete local Pydantic model |
| [Claude authentication](https://platform.claude.com/docs/en/manage-claude/authentication) | `anthropic-workspace-id` header for multi-workspace keys |
| [List Workspaces](https://platform.claude.com/docs/en/api/beta/organization/workspaces/list) | Read-only lookup with `include_default=true` and limit 1000; only an unambiguous active Default workspace from a complete response is selected |
| [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing) | Provider pricing reference; the application records token usage and limits attempts rather than estimating an account balance |
| [Agent Memory REST reference](https://surrealdb.com/docs/agent-memory/reference/rest-api) | Context-host `/facts` and `/query` routes, Bearer authentication, nested `scopes`/`lens` selectors, idempotency, trace and turn identifiers |
| [Agent Memory hosted quickstart](https://surrealdb.com/docs/agent-memory/quickstarts/hosted) | Context provisioning, scoped keys, and scope registration |
| [Agent Memory OpenAPI](https://github.com/surrealdb/surrealdb.js/blob/main/packages/memory/spec/openapi.json) | Scope registration through `POST /api/v1/{context_id}/scopes` using existing `scope:create` grants |

The memory adapter registers only an explicitly reported missing configured scope, then repeats the identical idempotent fact once. Unrelated errors do not trigger registration, retries, key changes, or permission escalation.

## Statistical references

Howard et al., [Time-uniform, nonparametric, nonasymptotic confidence sequences](https://arxiv.org/abs/1810.08240), provides primary research background for time-uniform inference. RiskGraph implements the simpler Hoeffding union-bound construction derived in [METHODS.md](METHODS.md), alongside standard Beta/Dirichlet inference and a betting e-process.

## Build North submission requirements

[Overview](https://build-north.devpost.com/), [rules](https://build-north.devpost.com/rules), and [sponsor resources](https://build-north.devpost.com/resources) describe the competition requirements. The submission deadline is October 25, 2026 at 11:59 p.m. ET. Requirements include public source, project documentation, applicable live links, and disclosure of prior work and AI tooling. The rules specify Canadian residence, age 18 or older, teams of up to four, and one submission per team. An optional video is limited to four minutes.

Sponsor recognition requires genuine platform use. The current implementation includes Render hosting, Claude API decisions, and SurrealDB Agent Memory storage and retrieval. Typed/time-aware policy supersession and shared memory between multiple application agents are extension targets, not current demonstrated capabilities. The validation record and public synthetic exports document completed integration behavior.
