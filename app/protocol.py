"""Versioned, case-bound workflow receipts. No model receives ledger authority."""
import hashlib
import json

VERSION = "handoff-v1"
ROLES = {
    "memory_retriever": ("service", "memory.read"),
    "refund_proposer": ("model_or_fixture", "refund.propose"),
    "advisory_critic": ("model", "proposal.comment"),
    "policy_reviewer": ("deterministic", "policy.review"),
    "execution_gate": ("deterministic", "ledger.authorize"),
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def handoff_receipts(event):
    """Directed acyclic protocol: recall -> propose -> [critic] -> review -> gate.

    Receipts bind the same run, sequence, case, proposal, critique and gate result.
    Hashes provide consistency checks, not signatures or authentic data sources.
    """
    context = {k: event[k] for k in ("run_id", "seq", "case", "proposal", "monitor", "review", "executed_cents")}
    context["critique"] = event.get("critique")
    context["memory_sources"] = event.get("memory", {}).get("hits", [])
    source = digest(context)
    roles = ["memory_retriever", "refund_proposer"]
    if event.get("critique") is not None:
        roles.append("advisory_critic")
    roles += ["policy_reviewer", "execution_gate"]
    previous, receipts = source, []
    for index, role in enumerate(roles):
        kind, capability = ROLES[role]
        receipt = {"version": VERSION, "run_id": event["run_id"], "sequence": event["seq"],
                   "case_id": event["case"]["id"], "stage": index, "role": role,
                   "kind": kind, "capability": capability, "context_sha256": source,
                   "previous_sha256": previous}
        receipt["sha256"] = digest(receipt)
        receipts.append(receipt)
        previous = receipt["sha256"]
    return receipts


def verify_handoffs(event):
    from .domain import Case, Proposal, inspect, score
    case, proposal = Case.model_validate(event["case"]), Proposal.model_validate(event["proposal"])
    monitor = inspect(case, proposal)
    executed = proposal.amount_cents if monitor["allowed"] and proposal.action == "refund" else 0
    gross = score(case, proposal)
    financials = {"executed_cents": executed, "gross_loss_cents": gross,
                  "residual_loss_cents": gross if executed else 0,
                  "prevented_loss_cents": gross if not executed else 0}
    return (event.get("monitor") == monitor and all(event.get(k) == v for k,v in financials.items())
            and event.get("handoffs") == handoff_receipts(event))
