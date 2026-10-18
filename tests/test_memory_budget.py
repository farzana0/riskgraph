import httpx
import pytest
from concurrent.futures import ThreadPoolExecutor
from app.domain import Proposal
from app.engine import Engine
from app.providers import ProviderError
from app.store import Store


class HostedMemory:
    configured = True
    def __init__(self):self.writes=[]
    def recall(self,category):return {"hits":[{"id":"h1","text":"Prior incident on " + category}],"trace":{"traceId":"trace-1"}}
    def remember(self,event):
        self.writes.append(event["id"])
        return {"turnId":"turn-1"}


class SpyAgent:
    def __init__(self):self.memories=[]
    def propose(self,case,mode,memories):
        self.memories.append(memories)
        return Proposal(action="refund",order_id=case.order.id,amount_cents=case.requested_cents,reason="fixture"),{}


def test_hosted_recall_shapes_decision_and_preserves_provenance():
    memory=HostedMemory();agent=SpyAgent()
    engine=Engine(Store(":memory:"),agent=agent,memory=memory)
    run=engine.create(42,10,use_memory=True)
    for i in range(10):result=engine.step(run["id"],i)
    assert all(hits[0]["id"]=="h1" for hits in agent.memories)
    assert memory.writes
    blocked=[e for e in result["events"] if not e["monitor"]["allowed"]]
    assert all(e["memory"]["turn_id"]=="turn-1" for e in blocked)
    assert all(e["memory"]["recall_trace_id"]=="trace-1" for e in result["events"])


def test_memory_failure_is_explicit_without_silent_local_fallback():
    class BrokenMemory(HostedMemory):
        def recall(self,category):raise httpx.ConnectError("unavailable")
        def remember(self,event):raise httpx.ConnectError("unavailable")
    engine=Engine(Store(":memory:"),memory=BrokenMemory())
    run=engine.create(42,10,use_memory=True)
    for i in range(10):result=engine.step(run["id"],i)
    assert all(e["memory"]["status"]=="surreal_recall_failed" for e in result["events"])
    assert all(e["memory"]["hits"]==[] for e in result["events"])
    assert any(e["memory"].get("write_status")=="surreal_write_failed" for e in result["events"])


def test_local_memory_changes_later_injection_decisions():
    engine=Engine(Store(":memory:"))
    run=engine.create(42,40,use_memory=True)
    for i in range(40):result=engine.step(run["id"],i)
    injections=[e for e in result["events"] if e["case"]["category"]=="injection"]
    assert len(injections)>1
    assert injections[0]["proposal"]["action"]=="refund"
    assert all(e["proposal"]["action"]=="escalate" for e in injections[1:])
    assert result["gross"]["anytime_upper_usd"] is None


def test_live_attempt_budget_persists_including_failed_calls(tmp_path,monkeypatch):
    monkeypatch.setenv("MAX_CLAUDE_CASES","1")
    class BrokenAgent:
        def propose(self,*args):raise ProviderError("invalid output")
    path=str(tmp_path/"budget.sqlite3")
    engine=Engine(Store(path),agent=BrokenAgent())
    run=engine.create(42,2,mode="claude")
    with pytest.raises(ProviderError):engine.step(run["id"],0)
    assert engine.store.attempts()==1
    reopened=Engine(Store(path),agent=BrokenAgent())
    with pytest.raises(ProviderError,match="budget exhausted"):reopened.step(run["id"],0)
    assert reopened.store.attempts()==1
    assert reopened.snapshot(run["id"])["gross"]["n"]==0


def test_attempt_budget_is_atomic_across_database_connections(tmp_path):
    path=str(tmp_path/"concurrent.sqlite3")
    stores=[Store(path),Store(path)]
    with ThreadPoolExecutor(max_workers=4) as executor:
        reserved=list(executor.map(lambda i:stores[i%2].reserve_attempt(5),range(20)))
    assert sum(reserved)==5
    assert stores[0].attempts()==5
