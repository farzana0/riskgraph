import json
import httpx
import pytest
from app.providers import Agent, AgentMemory, ProviderError


def test_anthropic_contract_and_usage(case,monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY","test-secret")
    def handler(request):
        assert str(request.url)=="https://api.anthropic.com/v1/messages"
        assert request.headers["x-api-key"]=="test-secret"
        body=json.loads(request.content)
        assert body["tool_choice"]["name"]=="propose_refund"
        assert "input_schema" in body["tools"][0]
        return httpx.Response(200,json={"stop_reason":"tool_use","content":[{"type":"tool_use","name":"propose_refund","input":{"action":"refund","order_id":"o1","amount_cents":10000,"reason":"eligible"}}],"usage":{"input_tokens":80,"output_tokens":20}})
    p,usage=Agent(httpx.Client(transport=httpx.MockTransport(handler))).propose(case,"claude",[])
    assert p.amount_cents==10000
    assert usage["output_tokens"]==20


@pytest.mark.parametrize("reply", [{"stop_reason":"max_tokens","content":[]},{"stop_reason":"tool_use","content":[{"type":"tool_use","name":"propose_refund","input":{"action":"refund","order_id":"o1","amount_cents":-1,"reason":"bad"}}]}, {"stop_reason":"tool_use","content":[{"type":"tool_use","name":"delete_all","input":{}}]}])
def test_invalid_provider_never_produces_action(case,monkeypatch,reply):
    monkeypatch.setenv("ANTHROPIC_API_KEY","test-secret")
    agent=Agent(httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=reply))))
    with pytest.raises(ProviderError):agent.propose(case,"claude",[])


def test_provider_error_does_not_leak_secret(case,monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY","test-secret")
    agent=Agent(httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(401,text="test-secret is bad"))))
    with pytest.raises(ProviderError) as error:agent.propose(case,"claude",[])
    assert "test-secret" not in str(error.value)


def test_agent_memory_routes_scoping_and_idempotency(monkeypatch):
    monkeypatch.setenv("SURREAL_MEMORY_URL","https://memory.example")
    monkeypatch.setenv("SURREAL_MEMORY_CONTEXT","riskgraph")
    monkeypatch.setenv("SURREAL_MEMORY_API_KEY","memory-secret")
    def handler(request):
        body=json.loads(request.content)
        assert request.headers["authorization"]=="Bearer memory-secret"
        if request.url.path.endswith("/query"):
            assert body["lens"]==[["org/riskgraph/demo"]]
            assert body["scopeView"]=="strict"
            return httpx.Response(200,json={"hits":[{"id":"m1","text":"Prior injection incident"}],"trace":{"traceId":"t1"}})
        assert request.url.path=="/api/v1/riskgraph/facts"
        assert body["scopes"]==[["org/riskgraph/demo"]]
        assert body["infer"]=="full"
        assert request.headers["idempotency-key"]=="e1"
        return httpx.Response(200,json={"turnId":"turn-1"})
    memory=AgentMemory(httpx.Client(transport=httpx.MockTransport(handler)))
    assert memory.recall("injection")["trace"]["traceId"]=="t1"
    event={"id":"e1","case":{"category":"injection","customer":"c1","order":{"id":"o1"}},"proposal":{"amount_cents":10000},"monitor":{"rules":["return_window"]},"gross_loss_cents":10000}
    assert memory.remember(event)["turnId"]=="turn-1"
