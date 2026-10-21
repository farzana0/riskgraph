# Orchestration framework decision

Reviewed against official sources on 21 October 2026.

RiskGraph is an assurance layer with a bounded refund workflow as its reference system. The current runtime is the repository's explicit proposal/review/gate state machine. It does not embed Hermes, OpenClaw, or openJiuwen. The second-model critic is optional and advisory; the policy reviewer and execution gate are deterministic components, not additional LLMs.

| Candidate | Official scope relevant to this project | Decision |
|---|---|---|
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) | Persistent assistant with skills, memory, tools, delegation, trajectory export and gateway interfaces | Evaluate as a future system under test through episode exports; no dependency in the reference runtime |
| [OpenClaw](https://docs.openclaw.ai/concepts/multi-agent) | Multi-agent routing with per-agent workspaces and session state; documentation distinguishes workspaces from hard sandboxing | Evaluate as a future system under test. Require explicit sandbox and tool-permission configuration before any execution integration |
| [openJiuwen agent-core](https://github.com/openJiuwen-ai/agent-core) | Python SDK for agent/workflow orchestration, runtime, checkpointing and model/tool integration | Closest candidate for an optional orchestration adapter after version-pinned integration tests; no SDK dependency added in this release |

The third candidate is openJiuwen. Framework selection is based on fit to the Python workflow and evaluation needs, not a measured safety ranking. No comparative security experiment across these three frameworks has been performed.

## Integration boundary

An external orchestrator should export one final adjudicated outcome per business episode, retaining its internal messages, agent IDs and provenance in its own secured trace store. The browser intake groups intermediate records by episode ID and rejects duplicate final outcomes, incomplete episodes, absent loss labels and non-integer money. Only numeric proposed/residual loss pairs and assessment settings reach the stateless RiskGraph endpoint.

This is a trace interchange interface, not an implemented native SDK adapter for these products. An adapter may propose actions or supply evidence; only the trusted execution gate may authorize a synthetic payment. Model output, memory, peer agreement and framework metadata never grant policy authority.

A future native adapter must pin a release and verify: role/tool allowlists, case-bound messages, timeout behavior, bounded delegation, replay handling, memory provenance, recovery semantics, and the correspondence between recorded and actually executed actions. It must pass the same failure campaign before its results are compared with the reference runtime.

## Scope of isolation

Current roles share one Python service process. Typed schemas, directed control flow and ledger transactions constrain application behavior. They are not operating-system sandboxing or protection against a compromised process, database, model provider or trusted order source. Production deployment requires separate principals, authenticated state sources and a payment service that enforces idempotency and limits independently.
