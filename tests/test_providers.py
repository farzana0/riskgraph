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
        assert body["tool_choice"]=={"type":"auto","disable_parallel_tool_use":True}
        assert body["thinking"]=={"type":"between_tools"}
        assert body["output_config"]=={"effort":"low"}
        assert body["tools"][0]["strict"] is True
        assert "input_schema" in body["tools"][0]
        schema=body["tools"][0]["input_schema"]
        assert schema["additionalProperties"] is False
        assert "minimum" not in schema["properties"]["amount_cents"]
        assert "maxLength" not in schema["properties"]["reason"]
        assert "100000" in schema["properties"]["amount_cents"]["description"]
        return httpx.Response(200,json={"stop_reason":"tool_use","content":[{"type":"tool_use","name":"propose_refund","input":{"action":"refund","order_id":"o1","amount_cents":10000,"reason":"eligible"}}],"usage":{"input_tokens":80,"output_tokens":20}})
    p,usage=Agent(httpx.Client(transport=httpx.MockTransport(handler))).propose(case,"claude",[])
    assert p.amount_cents==10000
    assert usage["output_tokens"]==20


@pytest.mark.parametrize("reply", [{"stop_reason":"max_tokens","content":[]},{"stop_reason":"end_turn","content":[{"type":"text","text":"No tool call"}]},{"stop_reason":"tool_use","content":[{"type":"tool_use","name":"propose_refund","input":{"action":"refund","order_id":"o1","amount_cents":-1,"reason":"bad"}}]}, {"stop_reason":"tool_use","content":[{"type":"tool_use","name":"propose_refund","input":{"action":"refund","order_id":"o1","amount_cents":10,"reason":"x"*601}}]}, {"stop_reason":"tool_use","content":[{"type":"tool_use","name":"delete_all","input":{}}]}])
def test_invalid_provider_never_produces_action(case,monkeypatch,reply):
    monkeypatch.setenv("ANTHROPIC_API_KEY","test-secret")
    agent=Agent(httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=reply))))
    with pytest.raises(ProviderError):agent.propose(case,"claude",[])


def test_provider_error_does_not_leak_secret(case,monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY","test-secret")
    agent=Agent(httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(401,text="test-secret is bad"))))
    with pytest.raises(ProviderError) as error:agent.propose(case,"claude",[])
    assert "test-secret" not in str(error.value)


@pytest.mark.parametrize("status,code", [(400,"invalid_request"),(401,"authentication"),(402,"credits"),(403,"permission"),(404,"not_found"),(429,"rate_limit"),(503,"http_error")])
def test_provider_failure_has_actionable_redacted_diagnostics(case,monkeypatch,status,code):
    monkeypatch.setenv("ANTHROPIC_API_KEY","test-secret")
    agent=Agent(httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(status,json={"error":{"message":"test-secret"}}))))
    with pytest.raises(ProviderError) as error:
        agent.propose(case,"claude",[])
    diagnostic=error.value.diagnostic
    assert diagnostic["code"]==code
    assert diagnostic["http_status"]==status
    assert "test-secret" not in json.dumps(diagnostic)


def test_anthropic_insufficient_credit_http_400_is_classified(case,monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY","test-secret")
    agent=Agent(httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(400,json={"error":{"message":"Your credit balance is too low. test-secret"}}))))
    with pytest.raises(ProviderError) as error:
        agent.propose(case,"claude",[])
    assert error.value.diagnostic["code"]=="credits"
    assert "test-secret" not in json.dumps(error.value.diagnostic)


def test_provider_timeout_is_distinct_from_bad_output(case,monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY","test-secret")
    def handler(request):raise httpx.ReadTimeout("test-secret",request=request)
    agent=Agent(httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ProviderError) as error:
        agent.propose(case,"claude",[])
    assert error.value.diagnostic["code"]=="timeout"
    assert "test-secret" not in str(error.value)


def test_sonnet_specific_thinking_not_sent_to_other_models(case,monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY","test-secret")
    monkeypatch.setenv("ANTHROPIC_MODEL","claude-sonnet-5")
    def handler(request):
        body=json.loads(request.content)
        assert "thinking" not in body
        assert body["tool_choice"]["type"]=="auto"
        return httpx.Response(200,json={"stop_reason":"tool_use","content":[{"type":"tool_use","name":"propose_refund","input":{"action":"escalate","order_id":"o1","amount_cents":0,"reason":"review"}}]})
    proposal,_=Agent(httpx.Client(transport=httpx.MockTransport(handler))).propose(case,"claude",[])
    assert proposal.action=="escalate"


def test_missing_scope_hint_does_not_expose_provider_body():
    from app.providers import failure_details
    request=httpx.Request("POST","https://memory.example/private-key")
    response=httpx.Response(400,request=request,json={"message":"Scope org/riskgraph/demo not registered; private-key"})
    with pytest.raises(httpx.HTTPStatusError) as error:response.raise_for_status()
    diagnostic=failure_details(error.value,"surreal")
    assert diagnostic["code"]=="missing_scope"
    assert "private-key" not in json.dumps(diagnostic)


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


def memory_fixture(monkeypatch,handler):
    monkeypatch.setenv('SURREAL_MEMORY_URL','https://memory.example')
    monkeypatch.setenv('SURREAL_MEMORY_CONTEXT','riskgraph')
    monkeypatch.setenv('SURREAL_MEMORY_API_KEY','memory-secret')
    event={'id':'e1','case':{'category':'injection','customer':'c1','order':{'id':'o1'}},'proposal':{'amount_cents':10000},'monitor':{'rules':['return_window']},'gross_loss_cents':10000}
    return AgentMemory(httpx.Client(transport=httpx.MockTransport(handler))),event


def test_missing_demo_scope_is_registered_once_with_same_idempotent_fact(monkeypatch):
    requests=[]
    def handler(request):
        requests.append(request)
        if len(requests)==1:
            return httpx.Response(400,json={'message':'Unknown scope org/riskgraph/demo'})
        if len(requests)==2:
            assert request.url.path.endswith('/scopes')
            assert json.loads(request.content)=={'path':'org/riskgraph/demo','displayName':'RiskGraph demo'}
            return httpx.Response(201,json={'path':'org/riskgraph/demo/'})
        assert request.url.path.endswith('/facts')
        assert request.content==requests[0].content
        assert request.headers['idempotency-key']==requests[0].headers['idempotency-key']=='e1'
        return httpx.Response(200,json={'turnId':'turn-1'})
    memory,event=memory_fixture(monkeypatch,handler)
    result=memory.remember(event)
    assert result['turnId']=='turn-1'
    assert result['riskgraph_scope_prepared'] is True
    assert len(requests)==3


@pytest.mark.parametrize('status,message',[(400,'Bad inference settings'),(403,'Scope access denied'),(429,'Rate limited'),(500,'Internal error')])
def test_other_memory_failures_do_not_trigger_scope_registration_or_retry(monkeypatch,status,message):
    requests=[]
    def handler(request):
        requests.append(request)
        return httpx.Response(status,json={'message':message})
    memory,event=memory_fixture(monkeypatch,handler)
    with pytest.raises(httpx.HTTPStatusError):memory.remember(event)
    assert len(requests)==1


def test_scope_registration_denial_does_not_attempt_grant_changes(monkeypatch):
    paths=[]
    def handler(request):
        paths.append(request.url.path)
        return httpx.Response(400,json={'message':'Unregistered scope'}) if len(paths)==1 else httpx.Response(403,json={'message':'Missing scope:create permission'})
    memory,event=memory_fixture(monkeypatch,handler)
    with pytest.raises(httpx.HTTPStatusError) as error:memory.remember(event)
    assert error.value.response.status_code==403
    assert paths==['/api/v1/riskgraph/facts','/api/v1/riskgraph/scopes']
