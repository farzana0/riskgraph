from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4
import os
import httpx
from .domain import generate, inspect, score, authorization
from .providers import Agent, AgentMemory, ProviderError, failure_details
from .risk import estimate, drift


def now():
    return datetime.now(timezone.utc).isoformat()


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

    def create(self, seed, count, mode="offline", use_memory=False):
        run = {"id": uuid4().hex, "seed": seed, "count": count, "mode": mode,
               "use_memory": use_memory, "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5") if mode == "claude" else "naive-fixture-v1",
               "created_at": now(), "status": "ready", "error": None,
               "policy_version": "refund-v1", "generator_version": "cases-v1"}
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
            if run["mode"] == "claude" and not self.store.reserve_attempt(int(os.getenv("MAX_CLAUDE_CASES", "200"))):
                raise BudgetExceeded("Workspace Claude attempt budget exhausted")
            case = generate(run["seed"], run["count"])[len(events)]
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
            gross = score(case, proposal)
            executed = proposal.amount_cents if monitor["allowed"] and proposal.action == "refund" else 0
            event = {"id": uuid4().hex, "run_id": run_id, "seq": len(events), "at": now(),
                     "mode": run["mode"], "case": case.model_dump(), "proposal": proposal.model_dump(),
                     "monitor": monitor, "gross_loss_cents": gross,
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
        gross = estimate([e["gross_loss_cents"] for e in events])
        residual = estimate([e["residual_loss_cents"] for e in events])
        for risk in (gross, residual):
            if run["use_memory"]:
                risk["anytime_upper_usd"] = None
                risk["bound_assumption"] = "Unavailable: adaptive memory changes the decision distribution. Bayesian interval is descriptive under a stationary approximation."
        return {"run": run, "events": events, "gross": gross, "residual": residual,
                "prevented_usd": sum(e["prevented_loss_cents"] for e in events) / 100,
                "executed_usd": sum(e["executed_cents"] for e in events) / 100,
                "blocked": sum(not e["monitor"]["allowed"] for e in events),
                "unnecessary_abstentions": sum(e["unnecessary_abstention"] for e in events),
                "drift": drift([e["gross_loss_cents"] > 0 for e in events]),
                "tokens": {key: sum(e["usage"].get(key, 0) for e in events) for key in ("input_tokens", "output_tokens")}}
