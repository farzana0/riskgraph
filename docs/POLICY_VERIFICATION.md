# Symbolic verification of the refund gate

## Property and result

Z3 4.15.3 reports **UNSAT** for:

    schema/domain constraints AND gate_allows AND specified_loss > 0

Within the encoded domain, there is no action allowed by the current refund gate that has positive specified unauthorized-payment loss. Integer money is bounded by the synthetic $1,000 cap; age and previously refunded amounts may be nonnegative integers. Non-refund actions score zero monetary loss and execute no payment in the reference workflow. Availability and service harm are separate properties.

This checks a narrow policy kernel. It does not prove the entire agent architecture, model, Python process, data source or external payment service safe.

## Connection to the implementation

`scripts/verify_policy.py` translates the current source AST of `app.domain.inspect` through a restricted whitelist: attribute comparisons, integer subtraction, action tests, nested conditional rule appends, and the final empty-rule-list verdict. It rejects unsupported statements, list resets, changed return structure and unrecognized expressions. Identifier equality is abstracted to integer identity classes; no ordering on identifiers is used.

The loss/authorization specification is encoded separately. Two thousand generated concrete examples compare every translated rule and scored loss with the Python implementations. This is a differential implementation check in addition to the symbolic result. It does not constitute a proof of the translator itself.

Six negative controls remove, in turn, order matching, ownership, date, balance, request limit and approval limit. Every weakened encoding admits a harmful counterexample. The generated witnesses are replayed through the actual Python gate and scorer; the complete gate rejects them. Counterexamples use coherent paid/refunded balances.

## Reproduce

Install the pinned development requirements and run:

    python scripts/verify_policy.py

The regular CI workflow reruns this check. Z3 is a development dependency; it is not added to the deployed service runtime. The [SMT-LIB query](examples/policy-soundness.smt2) and [result manifest](examples/policy-smt.json) include the checked property, source fingerprints, solver version, differential-example count and concrete negative controls. The result relies on the solver; no separately verified proof certificate is claimed.

## Trusted assumptions and exclusions

- Inputs satisfy the typed domain and refer to authentic, sufficiently current order/customer facts.
- The specified refund policy and monetary scoring definition are appropriate.
- The AST translator, SMT solver and Python integer/schema semantics behave as assumed.
- Payments execute only through the reference gate and ledger. Process compromise, direct tool access, stale external state, duplicate settlement and distributed races require additional controls.
- Hash handoff receipts check consistency of recorded facts. They do not establish source authenticity or replace execution verification.

Execution failures outside this kernel are explicitly represented in the separate [operational outcome models](OPERATIONAL_SCENARIOS.md). A zero policy-counterexample result cannot be used to assign them zero risk.

The underlying solver is described by de Moura and Bjørner, [Z3: an efficient SMT solver](https://www.microsoft.com/en-us/research/publication/z3-an-efficient-smt-solver/), TACAS 2008. The pinned Python package is [z3-solver 4.15.3.0](https://pypi.org/project/z3-solver/4.15.3.0/).
