"""Read-only policy reviewer and independently checkable decision evidence."""
import hashlib
import json
from .domain import Case, Proposal, authorization, inspect


def fingerprint(case, proposal):
    evidence = {"case": case.model_dump(), "proposal": proposal.model_dump()}
    return hashlib.sha256(json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def review_proposal(case: Case, proposal: Proposal, monitor, memories):
    """A deterministic review role can explain/route, but never override the gate.

    This is a policy review workflow role, not a second LLM or a formal proof.
    It consumes the same incident context as the proposal agent.
    """
    o = case.order
    checks = {
        "order_identity": proposal.order_id == o.id,
        "ownership": case.customer == o.owner,
        "refund_window": o.age_days <= 30,
        "remaining_balance": proposal.amount_cents <= max(0, o.paid_cents-o.refunded_cents),
        "requested_amount": proposal.amount_cents <= case.requested_cents,
        "automatic_approval": proposal.amount_cents <= 20000,
        "action_amount": proposal.amount_cents > 0 if proposal.action == "refund" else proposal.amount_cents == 0,
    }
    required = ["order_identity", "action_amount"] + (["ownership", "refund_window", "remaining_balance", "requested_amount", "automatic_approval"] if proposal.action == "refund" else [])
    consistent = all(checks[key] for key in required) == monitor["allowed"]
    return {"role": "policy_reviewer", "implementation": "deterministic_v1",
            "recommendation": proposal.action if monitor["allowed"] else "block",
            "checks": [{"name": key, "passed": checks[key], "required": key in required} for key in checks],
            "authorized_limit_cents": authorization(case), "policy_consistent": consistent,
            "memory_source_ids": [m.get("id") for m in memories if m.get("id")],
            "evidence_sha256": fingerprint(case, proposal),
            "authority": "Read-only review; the independent monitor is the execution gate"}


def verify_review(event):
    """Recompute all review fields and the original policy verdict from public facts."""
    case = Case.model_validate(event["case"])
    proposal = Proposal.model_validate(event["proposal"])
    verdict = inspect(case, proposal)
    expected = review_proposal(case, proposal, verdict, event.get("memory", {}).get("hits", []))
    return event.get("monitor") == verdict and event.get("review") == expected and expected["policy_consistent"]
