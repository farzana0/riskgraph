import json
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.providers import ProviderError


@pytest.fixture
def client(monkeypatch):
    for key in ["RISKGRAPH_ADMIN_TOKEN","ANTHROPIC_API_KEY","SURREAL_MEMORY_URL","SURREAL_MEMORY_CONTEXT","SURREAL_MEMORY_API_KEY"]:monkeypatch.delenv(key,raising=False)
    return TestClient(create_app(":memory:",seed_demo=False))


def test_end_to_end_run_and_retry_does_not_duplicate_execution(client):
    s=client.post("/api/runs",json={"seed":42,"count":12}).json()
    run_id=s["run"]["id"]
    for i in range(12):
        response=client.post(f"/api/runs/{run_id}/step",json={"expected_seq":i})
        assert response.status_code==200
    s=response.json()
    assert s["run"]["status"]=="complete"
    assert s["gross"]["failures"]>0
    assert s["residual"]["observed_loss_usd"]==0
    assert s["prevented_usd"]==s["gross"]["observed_loss_usd"]
    assert client.post(f"/api/runs/{run_id}/step",json={"expected_seq":0}).status_code==409
    assert len(client.get(f"/api/runs/{run_id}").json()["events"])==12
    export=client.get(f"/api/runs/{run_id}/export")
    assert "attachment" in export.headers["content-disposition"]
    assert export.json()["run"]["seed"]==42


def test_dashboard_and_security_headers(client):
    response=client.get("/")
    assert response.status_code==200
    assert "RiskGraph" in response.text
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert client.get("/static/app.js").status_code==200
    assert client.get("/healthz").json()["status"]=="ok"


def test_unauthorized_and_cross_origin_mutations(client,monkeypatch):
    monkeypatch.setenv("RISKGRAPH_ADMIN_TOKEN","operator-secret")
    protected=TestClient(create_app(":memory:",seed_demo=False))
    assert protected.post("/api/runs",json={}).status_code==401
    assert protected.post("/api/runs",json={},headers={"X-Operator-Token":"operator-secret"}).status_code==201
    assert client.post("/api/runs",json={},headers={"Origin":"https://evil.example"}).status_code==403
    assert protected.get("/api/config").status_code==200
    assert "operator-secret" not in protected.get("/api/config").text


@pytest.mark.parametrize("body", [{"count":0},{"count":201},{"mode":"random"},{"seed":-1},{"extra":"bad"}])
def test_bad_inputs(client,body):
    assert client.post("/api/runs",json=body).status_code==422


def test_live_requires_credentials(client):
    assert client.post("/api/runs",json={"mode":"claude"}).status_code==503


def test_provider_failure_does_not_count_as_safe_trial(monkeypatch):
    class BrokenAgent:
        def propose(self,*args):raise ProviderError("secret provider error")
    client=TestClient(create_app(":memory:",seed_demo=False,agent=BrokenAgent()))
    s=client.post("/api/runs",json={"count":1}).json();run_id=s["run"]["id"]
    response=client.post(f"/api/runs/{run_id}/step",json={"expected_seq":0})
    assert response.status_code==502
    assert "secret provider error" not in response.text
    result=client.get(f"/api/runs/{run_id}").json()
    assert result["events"]==[]
    assert result["gross"]["n"]==0
    assert result["run"]["status"]=="provider_error"


def test_memory_run_disables_stationary_bound(client):
    s=client.post("/api/runs",json={"seed":42,"count":1,"use_memory":True}).json()
    assert s["residual"]["anytime_upper_usd"] is None
    s=client.post(f'/api/runs/{s["run"]["id"]}/step',json={"expected_seq":0}).json()
    assert s["events"][0]["memory"]["status"]=="local_demo"


def test_persistence_survives_reopen(tmp_path,monkeypatch):
    path=str(tmp_path/"db.sqlite3")
    first=TestClient(create_app(path,seed_demo=False))
    s=first.post("/api/runs",json={"count":1}).json()
    first.post(f'/api/runs/{s["run"]["id"]}/step',json={"expected_seq":0})
    second=TestClient(create_app(path,seed_demo=False))
    restored=second.get(f'/api/runs/{s["run"]["id"]}').json()
    assert len(restored["events"])==1


def test_missing_run(client):
    assert client.get("/api/runs/unknown").status_code==404
    assert client.post("/api/runs/unknown/step",json={"expected_seq":0}).status_code==404
