from concurrent.futures import ThreadPoolExecutor
import json
from app.travel import generate,checks,outcome,current_offers,FAMILIES
from app.travel_calls import payload
from app.live_budget import LiveBudget as TravelBudget
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
        finally:b.db.close()
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


def test_large_haiku_tail_keeps_missing_adverse_endpoint_separate():
    from app.travel_scale import analyze
    c=generate();rows=[]
    for case in c:
        q=case['truth'];p={'action':'book','offer_id':q['valid_offer_id'],'traveller_id':case['observation']['authenticated_request']['traveller_id'],'quoted_total_cents':q['total_cents'],'reason':'Control'}
        rows.append({'case_id':case['id'],'initial_outcome':outcome(case,{'status':'complete','proposal':p})})
    rows[0]['initial_outcome']=outcome(c[0],{'status':'invalid_response'})
    a=analyze(c,rows,True)['arms'][MODELS[0]+'|0'];assert a['unresolved']==1 and a['tail'][0]['exact_upper'] is None
    assert 0<a['tail'][0]['adverse_or_unresolved_exact_upper']<1 and a['missing_loss_mean_range_usd']==[0,1000/32]


def test_scale_cases_are_fresh_and_forced_format_is_separate():
    from scripts.travel_scale import generate_scale
    from app.scale_calls import payload as forced
    cases=generate_scale();old=generate();assert len(cases)==5504
    assert {c['id'] for c in cases}.isdisjoint(c['id'] for c in old)
    assert {c['observation']['authenticated_request']['trip_id'] for c in cases}.isdisjoint(c['observation']['authenticated_request']['trip_id'] for c in old)
    p=forced(cases[0]['observation'],MODELS[0]);q=payload(cases[0]['observation'],MODELS[0]);assert p['messages']==q['messages'] and p['system']==q['system']
    assert p['tool_choice']['type']=='tool' and p['max_tokens']==512 and q['tool_choice']['type']=='auto'


def test_saved_review_requires_operator_and_uses_server_side_case(monkeypatch,tmp_path):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app import travel_live
    monkeypatch.setenv('RISKGRAPH_ADMIN_TOKEN','operator-test');monkeypatch.setenv('DATABASE_PATH',str(tmp_path/'app.sqlite3'))
    seen=[]
    def reject(case_id):seen.append(case_id);raise ValueError('Evidence preparing')
    monkeypatch.setattr(travel_live,'start_review',reject)
    client=TestClient(create_app(':memory:',seed_demo=False));body={'case_id':'scale-travel-wrong_date-1'}
    assert client.post('/api/travel-review',json=body).status_code==401 and not seen
    assert client.post('/api/travel-review',json={**body,'proposal':{}},headers={'X-Operator-Token':'operator-test'}).status_code==422 and not seen
    assert client.post('/api/travel-review',json=body,headers={'X-Operator-Token':'operator-test'}).status_code==409 and seen==[body['case_id']]


def test_live_case_opaque_ids_preserve_quote_and_ledger_contract():
    from app.travel_live import live_case
    for family in FAMILIES:
        c=live_case(family,2026102499);assert c==live_case(family,2026102499)
        q=c['truth'];assert all(len(x['offer_id'])==22 for x in c['observation']['quotes'])
        p={'action':'book','offer_id':q['valid_offer_id'],'traveller_id':c['observation']['authenticated_request']['traveller_id'],'quoted_total_cents':q['total_cents'],'reason':'Opaque-ID control'}
        assert checks(c['observation'],p)['allowed']
