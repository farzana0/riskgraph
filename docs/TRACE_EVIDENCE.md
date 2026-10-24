# Trace evidence and source-transfer projection

RiskGraph accepts normalized JSON episodes at `/evidence`. Importing or projecting traces does not send them to Claude. A local preview sends nothing to the server. Saving, reading and projecting a private batch requires the existing operator token. Batches are stored under the persistent database directory in `private-evidence`, with restricted file permissions; no public file mount or listing exposes them. Operator access is shared service access, not a separate multi-tenant identity system. Remove credentials and personal information before importing.

## Sampling and labels

An episode is one request or task attempt. Its agent events form a directed acyclic graph through `parent_ids`; events do not inflate the trial count. Repeated episode IDs within a batch are rejected. Each batch declares `source` (`observed`, `simulation` or `illustration`), the system version, a simulation reference configuration and a bounded loss cap in cents. Saving the same evidence as a new batch cannot add to the sample: each projection uses exactly one selected batch and never pools saved batches automatically.

A reviewed episode requires a review reference. The reference is an operator attestation, not automatic verification that an external incident occurred. Missing or unreviewed potential losses remain unresolved, even if an executed loss is recorded as zero. Potential and executed losses are different fields. An illustration is never admitted to the observed lane. There are no real observations in the public demo unless an operator supplies them privately. The example JSON is explicitly an illustration.

## Explicit mixture

For a loss threshold t, the projection is

`P(L > t) = (1-epsilon) sum_s w_s [(1-rho) p_sim,s + rho p_obs,s] + epsilon q_unseen`.

Scenario weights w sum to one. Rho is an assumed observed-source transfer share; epsilon is an assumed unmodeled-failure mass; q_unseen ranges over [0,1]. These are scenario assumptions, not learned production frequencies. Deliberately oversampled stress tests and observed traffic are not pooled. Matching the reference configuration is a declared comparison mapping, not proof that a deployed system is exchangeable with the simulated agent.

Each source/scenario retains its own episode counts. Nonempty source cells use the declared Jeffreys Beta working model. Missing outcomes are bounded by assigning all unresolved labels either below or above the threshold. A source/scenario with no observations retains the full [0,1] range instead of a fabricated posterior point. The envelope combines the lower 2.5th percentile and upper 97.5th percentile, then adds the unmodeled component at both extremes. This is a marginal model-based sensitivity envelope, not a frequentist coverage guarantee. It inherits the fixed-quota and small-sample working-model limitations of the simulation study. The separate simultaneous independent-episode bounds on `/compare` have a different target and interpretation.

Unknown scenario names are accepted into the source ledger and explicitly reported as outside the tested catalogue. They are not silently relabeled or added to a known family. Using such a batch with positive observed share requires a nonzero unmodeled-mass assumption. That assumption is not inferred from the number of novel labels; distributional shift and discoveries require separate validation.

## Format

See [the illustration](examples/trace-format-illustration.json). Set `source` truthfully and use a real review reference only for independently reviewed outcomes. Null means unknown; zero means reviewed and known to be zero. Reference configurations have the form `claude-haiku-5-5|none|0` (model, memory none/selected, reviewer 0/1). The example may be checked and privately saved but cannot contribute to an observed-source projection.

The implementation uses the existing [Anthropic structured-output contract](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) for synthetic model decisions and the [SurrealDB hosted memory contract](https://surrealdb.com/docs/agent-memory/quickstarts/hosted) for frozen procedural retrieval. Imported real traces are neither automatically written into memory nor used to tune the held-out experiment.
