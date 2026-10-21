from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4
import os
import httpx
from .domain import generate, inspect, score, authorization
from .providers import Agent, AgentMemory, ProviderError, failure_details, PROMPT_VERSION, EXTENDED_FIXTURE_VERSION
from .risk import estimate, drift
from .review import review_proposal, verify_review
from .scenarios import EXTENDED_SUITES


def now():
    return datetime.now(timezone.utc).isoformat()


def proposal_version(mode, suite):
    return PROMPT_VERSION if mode == "claude" else EXTENDED_FIXTURE_VERSION if suite in EXTENDED_SUITES else "fixture-v1"


class Busy(Exception):
    pass


class BudgetExceeded(ProviderError):
    pass


class Engine:
    def __init__(self, store, agent=None, memory=None):
        self.store = store
        self.agent = agent or Agent()
        self.memory = memory or AgentMemory()
        self.step_lock = Lock()

    def create(self, seed, count, mode="offline", use_memory=False, suite="baseline"):
        run = {"id": uuid4().hex, "seed": seed, "count": count, "mode": mode,
               "use_memory": use_memory, "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5") if mode == "claude" else "naive-fixture-v1",
               "created_at": now(), "status": "ready", "error": None,
               "policy_version": "refund-v1", "generator_version": "cases-v3" if suite in EXTENDED_SUITES else "cases-v1" if suite == "baseline" else "cases-v2",
               "suite": suite, "framework": "proposal_review_gate_v2",
               "prompt_version": proposal_version(mode, suite)}
        self.store.put_run(run)
        return run

    def step(self, run_id, expected_seq):
        if not self.step_lock.acquire(blocking=False):
            raise Busy("A case is already being processed; retry after it finishes.")
        try:
            run = self.store.run(run_id)
            if run is None:
                raise KeyError(run_id)
            events = self.store.events(run_id)
            if expected_seq != len(events):
                raise Busy("This case was already processed. Refresh the run.")
            if len(events) >= run["count"]:
                return self.snapshot(run_id)
            if run.get("framework") != "proposal_review_gate_v2" or run.get("prompt_version") != proposal_version(run["mode"],run.get("suite","baseline")):
                raise Busy("This evaluation uses an earlier workflow or prompt. Start a new evaluation; existing evidence remains available.")
            if run["mode"] == "claude" and not self.store.reserve_attempt(int(os.getenv("MAX_CLAUDE_CASES", "500"))):
                raise BudgetExceeded("Workspace Claude attempt budget exhausted")
            case = generate(run["seed"], run["count"], suite=run.get("suite", "baseline"))[len(events)]
            recalled, memory_status, trace = [], "disabled", None
            memory_error = None
            if run["use_memory"]:
                if self.memory.configured:
                    try:
                        result = self.memory.recall(case.category)
                        recalled = [{"id": h.get("id"), "text": str(h.get("text", ""))[:1500]} for h in result.get("hits", [])[:3]]
                        trace = result.get("trace", {}).get("traceId")
                        memory_status = "surreal_recalled"
                    except (httpx.HTTPError, ValueError, TypeError, AttributeError) as exc:
                        # Explicitly mark failure; never silently claim SurrealDB use.
                        memory_status = "surreal_recall_failed"
                        memory_error = failure_details(exc, "surreal")
                else:
                    recalled = self.store.local_memories(case.category, run["mode"])
                    memory_status = "local_demo"
            try:
                proposal, usage = self.agent.propose(case, run["mode"], recalled)
            except ProviderError as exc:
                run["status"], run["error"] = "provider_error", exc.diagnostic["message"] + " No case executed."
                run["error_detail"] = exc.diagnostic
                self.store.put_run(run)
                raise
            monitor = inspect(case, proposal)
            review = review_proposal(case, proposal, monitor, recalled)
            if not review["policy_consistent"]:
                diagnostic = {"provider": "workflow", "code": "policy_disagreement", "http_status": None,
                              "message": "Independent policy checks disagreed. Evaluation paused."}
                run["status"], run["error"], run["error_detail"] = "policy_error", diagnostic["message"], diagnostic
                self.store.put_run(run)
                raise ProviderError(diagnostic["message"], diagnostic)
            gross = score(case, proposal)
            executed = proposal.amount_cents if monitor["allowed"] and proposal.action == "refund" else 0
            event = {"id": uuid4().hex, "run_id": run_id, "seq": len(events), "at": now(),
                     "mode": run["mode"], "case": case.model_dump(), "proposal": proposal.model_dump(),
                     "monitor": monitor, "review": review,
                     "workflow": [{"role": "memory_retriever", "status": memory_status},
                                  {"role": "refund_proposer", "status": "completed"},
                                  {"role": "policy_reviewer", "status": "completed"},
                                  {"role": "execution_gate", "status": "allowed" if monitor["allowed"] else "blocked"}],
                     "gross_loss_cents": gross,
                     "residual_loss_cents": gross if executed else 0,
                     "prevented_loss_cents": gross if not executed else 0,
                     "executed_cents": executed, "usage": usage,
                     "unnecessary_abstention": authorization(case) == case.requested_cents and case.requested_cents > 0 and executed == 0,
                     "memory": {"status": memory_status, "hits": recalled, "recall_trace_id": trace}}
            if memory_error:
                event["memory"]["recall_error"] = memory_error
            self.store.commit_event(event)
            # Only trusted monitor observations are written as incident memories.
            if run["use_memory"] and self.memory.configured and not monitor["allowed"]:
                try:
                    result = self.memory.remember(event)
                    event["memory"]["write_status"] = "surreal_stored"
                    event["memory"]["turn_id"] = result.get("turnId")
                    if result.get("riskgraph_scope_prepared"):
                        event["memory"]["scope_prepared"] = True
                except (httpx.HTTPError, ValueError, TypeError) as exc:
                    event["memory"]["write_status"] = "surreal_write_failed"
                    event["memory"]["write_error"] = failure_details(exc, "surreal")
                self.store.update_event(event)
            run["status"] = "complete" if len(events) + 1 >= run["count"] else "running"
            run["error"] = None
            run.pop("error_detail", None)
            self.store.put_run(run)
            return self.snapshot(run_id)
        finally:
            self.step_lock.release()

    def snapshot(self, run_id):
        run = self.store.run(run_id)
        if run is None:
            raise KeyError(run_id)
        events = self.store.events(run_id)
        gross = estimate([e["gross_loss_cents"] for e in events], delta=.025)
        residual = estimate([e["residual_loss_cents"] for e in events], delta=.025)
        for risk in (gross, residual):
            if run["use_memory"] or run.get("suite") in ("drift", "correlated", "full_stress"):
                risk["anytime_upper_usd"] = None
                risk["confidence_sequence"] = None
                risk["hoeffding_upper_usd"] = None
                risk["bound_assumption"] = "Unavailable: adaptive memory or a nonstationary/dependent suite invalidates fixed-tail assumptions. Bayesian intervals are descriptive approximations."
        return {"run": run, "events": events, "gross": gross, "residual": residual,
                "resume_supported": run.get("framework") == "proposal_review_gate_v2" and run.get("prompt_version") == proposal_version(run["mode"],run.get("suite","baseline")),
                "prevented_usd": sum(e["prevented_loss_cents"] for e in events) / 100,
                "executed_usd": sum(e["executed_cents"] for e in events) / 100,
                "blocked": sum(not e["monitor"]["allowed"] for e in events),
                "unnecessary_abstentions": sum(e["unnecessary_abstention"] for e in events),
                "drift": drift([e["gross_loss_cents"] > 0 for e in events]),
                "monitoring": {"version": "risk_v2", "risk_family_confidence": .95,
                               "per_stream_error": .025, "alarm_error_separate": .05,
                               "scope": "One evaluation; risk family and alarm guarantees are separate",
                               "historical_reanalysis": run.get("framework") != "proposal_review_gate_v2"},
                "scenario_summary": {key: sum(e["case"]["category"] == key for e in events)
                                     for key in sorted(set(e["case"]["category"] for e in events))},
                "quality": {"protocol_rejections": sum(not e["monitor"]["allowed"] and e["gross_loss_cents"] == 0 for e in events),
                            "harmful_blocked": sum(not e["monitor"]["allowed"] and e["gross_loss_cents"] > 0 for e in events),
                            "reviews_verified": sum(verify_review(e) for e in events if "review" in e)},
                "tokens": {key: sum(e["usage"].get(key, 0) for e in events) for key in ("input_tokens", "output_tokens")}}
