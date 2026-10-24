from concurrent.futures import ThreadPoolExecutor
import json
from app.travel import generate,checks,outcome,current_offers,FAMILIES
from app.travel_calls import TravelBudget,payload
from app.providers import MODELS


def test_all_travel_families_have_valid_choices_and_adjudicated_traps():
    cases=generate();assert cases==generate() and len(cases)==32
    assert len(set(c['family'] for c in cases))==8
    for c in cases:
        obs=c['observation'];req=obs['authenticated_request'];truth=c['truth']
        p={'action':'book','offer_id':truth['valid_offer_id'],'traveller_id':req['traveller_id'],'quoted_total_cents':truth['total_cents'],'reason':'Independent test'}
        good=checks(obs,p);assert good['allowed'] and good['proposed_loss_cents']==0
        q=current_offers(obs)[truth['trap_offer_id']];p.update(offer_id=q['offer_id'],quoted_total_cents=q['base_cents']+sum(q['fee_cents']))
        bad=checks(obs,p);assert not bad['allowed'] and bad['proposed_loss_cents']>0
        assert outcome(c,{'status':'complete','proposal':p})['residual_loss_cents']==0


def test_missing_proposal_keeps_unknown_exposure_but_known_zero_execution():
    c=generate()[0];r=outcome(c,{'status':'invalid_response'});assert not r['resolved'] and r['proposed_loss_cents'] is None and r['executed_cents']==r['residual_loss_cents']==0
    p=payload(c['observation'],MODELS[0]);assert 'truth' not in json.dumps(p) and 'valid_offer_id' not in json.dumps(p)


def test_travel_reservations_are_atomic_across_connections(tmp_path):
    path=tmp_path/'budget.sqlite3';TravelBudget(path,1,50)
    def reserve(i):
        b=TravelBudget(path,1,50)
        try:b.acquire(str(i),.4);return True
        except RuntimeError:return False
    with ThreadPoolExecutor(6) as pool:results=list(pool.map(reserve,range(12)))
    assert sum(results)==2 and TravelBudget(path,1,50).totals()['accounted_estimated_usd']<=1


def test_public_travel_routes_are_read_only_and_live_requires_operator(monkeypatch,tmp_path):
    from fastapi.testclient import TestClient
    from app.main import create_app
    monkeypatch.setenv('RISKGRAPH_ADMIN_TOKEN','private-test-token')
    monkeypatch.setenv('DATABASE_PATH',str(tmp_path/'app.sqlite3'))
    client=TestClient(create_app(':memory:',seed_demo=False))
    assert client.get('/').status_code==200 and 'home.css' in client.get('/').text
    assert client.get('/travel').status_code==200
    assert client.get('/api/travel-stress').json()['cases']==6000
    assert client.post('/api/travel-live',json={}).status_code==401
    assert client.post('/api/travel-live',json={},headers={'X-Operator-Token':'private-test-token'}).status_code==409
    assert client.get('/api/travel-live?run=../invalid').status_code==404
