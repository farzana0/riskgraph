import copy
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import httpx
import pytest
from app.domain import Case, Proposal, inspect, score
from app.hardcases import generate_hard, HINTS, FAMILIES, digest
from app.hardbench import ResearchBudget, model_call, outcome, summarize, MODELS
from app.providers import Agent


def test_frozen_hard_cases_have_independently_reconstructible_oracles():
    cases = generate_hard(2102137,4)
    assert len(cases)==32 and all(sum(c['family']==f for c in cases)==4 for f in FAMILIES)
    assert digest(cases)==digest(generate_hard(2102137,4))
    assert set(c['id'] for c in cases).isdisjoint(c['id'] for c in generate_hard(2102131,1))
    for c in cases:
        o=c['observation']; records=o['authenticated_connector_records']; t=c['truth']['order']
        assert 'truth' not in o and 'expected_refund_cents' not in json.dumps(o)
        assert c['id'] not in json.dumps(HINTS)
        r=next(r for r in records if r['connector'] not in ('orders','accounts')) if c['family'] not in ('identity_join','tool_injection','elapsed_time') else None
        if c['family']=='settlement_ledger':
            paid=sum(e['cents'] for e in r['events'] if e['kind']=='capture' and e['status']=='settled')
            spent=sum(e['cents'] for e in r['events'] if e['kind']=='refund' and e['status'] in ('posted','pending'))
            assert (paid,spent)==(t['paid_cents'],t['refunded_cents'])
        elif c['family']=='reversal_graph':
            unique={e['id']:e for e in r['events']}; cancelled={e['reverses'] for e in unique.values() if e['type']=='reversal'}
            spent=sum(e['cents'] for e in unique.values() if e['type']=='refund' and e['id'] not in cancelled)
            assert spent==t['refunded_cents']
        elif c['family']=='elapsed_time':
            r=next(r for r in records if r['connector']=='orders')
            age=int((datetime.fromisoformat(r['evaluated_at'])-datetime.fromisoformat(r['paid_at'])).total_seconds()//86400)
            assert age==t['age_days']
        elif c['family']=='currency_rounding':
            rate=r['usd_cents_per_source_minor']; remaining=(r['paid_source_minor']-sum(r['refunds_source_minor']))*rate['numerator']//rate['denominator']
            assert remaining==t['paid_cents']-t['refunded_cents']
        elif c['family']=='snapshot_precedence':
            assert max(r['snapshots'],key=lambda s:s['sequence'])['refunded_cents']==t['refunded_cents']
        elif c['family']=='batch_reservations':
            spent=sum(e['amount_cents'] for e in r['reservations'] if e['status']=='active' and e['order_id']==t['id'])
            assert spent==t['refunded_cents']
        case=Case.model_validate(c['truth'])
        expected=c['expected_refund_cents']
        proposal=Proposal(action='refund' if expected else 'escalate',order_id=case.order.id,amount_cents=expected,reason='Independent oracle')
        assert inspect(case,proposal)['allowed'] and score(case,proposal)==0


def test_research_budget_is_persistent_and_never_retries_unknown_calls(tmp_path):
    path=tmp_path/'study.sqlite3'; b=ResearchBudget(path,max_usd=.03,max_calls=2)
    assert b.acquire('first',.02) is None
    with pytest.raises(RuntimeError,match='unknown'): b.acquire('first',.02)
    with pytest.raises(RuntimeError,match='allowance'): b.acquire('second',.02)
    b.finish('first',{'status':'complete'},.005)
    assert b.acquire('first',.02)=={'status':'complete'}
    assert b.acquire('second',.02) is None
    b.finish('second',{'status':'provider_error'})
    with pytest.raises(RuntimeError): b.acquire('third',.001)
    assert ResearchBudget(path).totals()['requests_reserved']==2


def test_research_budget_reservation_is_atomic_under_threads(tmp_path):
    b=ResearchBudget(tmp_path/'study.sqlite3',max_usd=1,max_calls=3)
    def attempt(i):
        try: b.acquire(str(i),.1); return 1
        except RuntimeError:return 0
    with ThreadPoolExecutor(8) as pool:
        assert sum(pool.map(attempt,range(30)))==3
    assert b.totals()['requests_reserved']==3


def test_pinned_design_rejects_after_the_fact_changes(tmp_path):
    b=ResearchBudget(tmp_path/'study.sqlite3')
    b.pin({'cases':'abc'});b.pin({'cases':'abc'})
    with pytest.raises(ValueError,match='changed'):b.pin({'cases':'different'})


def test_corrective_critic_can_fix_or_introduce_harm_and_gate_remains_separate():
    c=next(c for c in generate_hard(2102137,4) if c['expected_refund_cents']>0 and c['truth']['order']['refunded_cents']>0)
    expected=c['expected_refund_cents']
    good={'status':'complete','proposal':{'action':'refund','order_id':c['truth']['order']['id'],'amount_cents':expected,'reason':'Calculated'}}
    bad=copy.deepcopy(good);bad['proposal']['amount_cents']=min(100000,c['truth']['order']['paid_cents']+1)
    assert outcome(c,good)['task_failure'] is False
    scored=outcome(c,bad)
    assert scored['proposed_loss_cents']>0 and scored['residual_loss_cents']==0 and scored['task_failure']
    invalid=outcome(c,{'status':'invalid_response'})
    assert invalid['proposed_loss_cents'] is None and not invalid['resolved'] and invalid['task_failure']


def test_provider_requests_exclude_oracle_and_use_separate_review_call(tmp_path,monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY','test-key');monkeypatch.setenv('ANTHROPIC_WORKSPACE_ID','wrkspc_test')
    case=generate_hard(2102137,1)[0]
    expected=case['expected_refund_cents']
    proposal={'action':'refund' if expected else 'escalate','order_id':case['truth']['order']['id'],'amount_cents':expected,'reason':'Computed'}
    requests=[]
    def handler(request):
        payload=json.loads(request.content);requests.append(payload)
        assert 'expected_refund_cents' not in request.content.decode() and '"truth"' not in request.content.decode()
        return httpx.Response(200,json={'stop_reason':'tool_use','content':[{'type':'tool_use','name':'propose_refund','input':proposal}],'usage':{'input_tokens':100,'output_tokens':50}})
    agent=Agent(httpx.Client(transport=httpx.MockTransport(handler)))
    budget=ResearchBudget(tmp_path/'study.sqlite3')
    initial=model_call(agent,budget,case['observation'],[],MODELS[0],key='proposer')
    corrected=model_call(agent,budget,case['observation'],[],MODELS[1],original=initial['proposal'],key='critic')
    assert initial['status']==corrected['status']=='complete' and budget.totals()['requests_reserved']==2
    assert len(requests)==2 and 'untrusted_initial_proposal' in requests[1]['messages'][0]['content']
    model_call(agent,budget,case['observation'],[],MODELS[0],key='proposer')
    assert len(requests)==2
    model_call(agent,budget,case['observation'],[],MODELS[0],key='larger-budget',max_tokens=2048)
    assert requests[-1]['max_tokens']==2048 and budget.totals()['requests_reserved']==3
    with pytest.raises(ValueError):model_call(agent,budget,{},[],MODELS[0],max_tokens=1)


def test_failed_provider_calls_are_charged_and_do_not_leak_response(tmp_path,monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY','private-test-key');monkeypatch.setenv('ANTHROPIC_WORKSPACE_ID','wrkspc_test')
    agent=Agent(httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(429,json={'error':{'message':'private-test-key'}}))))
    budget=ResearchBudget(tmp_path/'study.sqlite3')
    result=model_call(agent,budget,{},[],MODELS[1],key='failed')
    assert result['status']=='provider_error' and result['cost_is_reserve']
    assert 'private-test-key' not in json.dumps(result) and budget.totals()['accounted_estimated_usd']>0


def test_factorial_analysis_keeps_failed_attempts_and_nonzero_uncertainty():
    case=generate_hard(2102137,1)[0];cells=[]
    expected=case['expected_refund_cents']
    completion={'status':'complete','proposal':{'action':'refund' if expected else 'decline','order_id':case['truth']['order']['id'],'amount_cents':expected,'reason':'test'}}
    for m in MODELS:
        for memory in (False,True):
            cells.append({'model':m,'memory':memory,'case_id':case['id'],'index':0,'initial_outcome':outcome(case,completion),'corrected_outcome':outcome(case,completion)})
    result=summarize([case],cells)
    assert len(result['arms'])==8 and len(result['comparisons'])==12
    assert all(a['proposed']['expected_loss_usd']>0 for a in result['arms'])
    assert all(c['conditional_difference_ci95_usd'][0]<0<c['conditional_difference_ci95_usd'][1] for c in result['comparisons'])
    cells[0]['corrected_outcome']=outcome(case,{'status':'invalid_response'})
    result=summarize([case],cells)
    assert result['arms'][1]['unresolved_episodes']==1 and result['arms'][1]['task_failures']==1


def test_public_study_selection_uses_fixed_paths_and_keeps_primary_available(tmp_path,monkeypatch):
    from app.main import create_app
    from fastapi.testclient import TestClient
    monkeypatch.setenv('DATABASE_PATH',str(tmp_path/'app.sqlite3'))
    primary={'status':'complete','cases':[{}]*32,'design':{'settings':{'max_tokens':900}}}
    high={'status':'running','cases':[{}]*16,'design':{'settings':{'max_tokens':2048}}}
    (tmp_path/'hard-benchmark.json').write_text(json.dumps(primary))
    (tmp_path/'high-budget').mkdir();(tmp_path/'high-budget'/'hard-benchmark.json').write_text(json.dumps(high))
    client=TestClient(create_app(':memory:',seed_demo=False))
    assert client.get('/api/hard-benchmark').json()['selected']=='primary'
    assert client.get('/api/hard-benchmark?study=high_budget').json()['study']['design']['settings']['max_tokens']==2048
    high['status']='complete';(tmp_path/'high-budget'/'hard-benchmark.json').write_text(json.dumps(high))
    assert client.get('/api/hard-benchmark').json()['selected']=='high_budget'
    assert client.get('/api/hard-benchmark?study=../../secrets').status_code==422
