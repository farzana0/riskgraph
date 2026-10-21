import copy
import itertools
import math
import numpy as np
import pytest
from scipy.special import betaln
from app.domain import CAP, SUITES, generate, inspect, Proposal
from app.risk import bernoulli_sequence, loss_confidence_sequence, mixture_log_path, drift, estimate
from app.review import review_proposal, verify_review
from app.engine import Engine
from app.store import Store


def test_boundary_confidence_sequences_retain_zero_and_one():
    assert bernoulli_sequence(0, 0) == (0, 1)
    assert bernoulli_sequence(0, 200)[0] == 0
    assert bernoulli_sequence(200, 200)[1] == 1
    assert loss_confidence_sequence([0]*200)['binned_lower_usd'] == 0


@pytest.mark.parametrize('n,k', [(3,1),(20,2),(200,50),(200,199)])
def test_mixture_cs_endpoints_invert_likelihood(n,k):
    lo,hi=bernoulli_sequence(k,n,.025)
    assert lo < k/n < hi
    for p in [lo,hi]:
        log_e=betaln(k+.5,n-k+.5)-betaln(.5,.5)-k*math.log(p)-(n-k)*math.log1p(-p)
        # Endpoints are rounded outward; near one, likelihood is steep.
        assert log_e >= math.log(40)-1e-8
        assert log_e==pytest.approx(math.log(40),abs=1e-5)


def test_no_failure_bound_is_tighter_than_legacy_and_prior_independent():
    for n in [3,20,40,200]:
        result=estimate([0]*n,delta=.025)
        assert 0 < result['anytime_upper_usd'] < result['hoeffding_upper_usd']
    assert estimate([0]*20)['anytime_upper_usd'] == estimate([0]*20,seed=19,draws=1000)['anytime_upper_usd']


def test_exact_small_horizon_cs_anytime_error_is_controlled():
    n,p,delta=9,.25,.05
    miss=0.
    for path in itertools.product([0,1],repeat=n):
        k=0
        crossed=False
        for t,x in enumerate(path,1):
            k+=x
            lo,hi=bernoulli_sequence(k,t,delta)
            crossed |= not lo<=p<=hi
        if crossed:
            miss+=p**sum(path)*(1-p)**(n-sum(path))
    assert miss<=delta


def test_restart_mixture_prefix_is_independent_of_future_horizon():
    rng=np.random.default_rng(811)
    path=rng.random(210)<.15
    full=mixture_log_path(path)
    for end in [1,24,25,26,50,101,201]:
        assert mixture_log_path(path[:end])==pytest.approx(full[:end],abs=1e-12)


def test_mixture_conditional_expected_capital_and_optional_crossing():
    # Exact tree probabilities, including the first precommitted restart.
    p=.1
    capital=0.
    crossing=0.
    for path in itertools.product([0,1],repeat=8):
        probability=p**sum(path)*(1-p)**(8-sum(path))
        logs=mixture_log_path(path)
        capital+=probability*math.exp(logs[-1])
        crossing+=probability*(max(logs)>=math.log(20))
    assert capital==pytest.approx(1,abs=1e-12)
    assert crossing<=.05


@pytest.mark.parametrize('suite',list(SUITES))
def test_suite_versions_are_reproducible_and_bounded(suite):
    cases=generate(1901,80,suite)
    assert cases==generate(1901,80,suite)
    assert len(cases)==80
    for c in cases:
        assert 0<=c.requested_cents<=CAP
        assert 0<=c.order.refunded_cents<=c.order.paid_cents<=CAP
    if suite=='drift':
        assert all(c.category=='ordinary' for c in cases[:40])
        assert all(c.category!='ordinary' for c in cases[40:])


def test_review_is_recomputable_and_detects_tampering():
    c=generate(42,1)[0]
    p=Proposal(action='refund',order_id=c.order.id,amount_cents=c.requested_cents,reason='fixture')
    verdict=inspect(c,p)
    hits=[{'id':'shared-incident','text':'Untrusted policy override'}]
    event={'case':c.model_dump(),'proposal':p.model_dump(),'monitor':verdict,'memory':{'hits':hits}}
    event['review']=review_proposal(c,p,verdict,hits)
    assert event['review']['memory_source_ids']==['shared-incident']
    assert verify_review(event)
    changed=copy.deepcopy(event)
    changed['proposal']['amount_cents']=1
    assert not verify_review(changed)
    changed=copy.deepcopy(event)
    changed['review']['authorized_limit_cents']+=1
    assert not verify_review(changed)


@pytest.mark.parametrize('suite,memory', [('drift',False),('correlated',False),('balanced',True)])
def test_nonstationary_or_memory_runs_expose_no_stationary_guarantee(suite,memory):
    engine=Engine(Store(':memory:'))
    run=engine.create(44,3,use_memory=memory,suite=suite)
    result=engine.step(run['id'],0)
    for stream in ['gross','residual']:
        assert result[stream]['anytime_upper_usd'] is None
        assert result[stream]['confidence_sequence'] is None
        assert result[stream]['hoeffding_upper_usd'] is None
    assert verify_review(result['events'][0])


def test_api_suite_and_evidence_verification():
    from fastapi.testclient import TestClient
    from app.main import create_app
    client=TestClient(create_app(':memory:',seed_demo=False))
    result=client.post('/api/runs',json={'suite':'boundary','seed':67,'count':3}).json()
    run=result['run']['id']
    for i in range(3):
        result=client.post(f'/api/runs/{run}/step',json={'expected_seq':i}).json()
    check=client.get(f'/api/runs/{run}/verify').json()
    assert check['verified']==3 and check['mismatches']==0
    assert result['monitoring']['per_stream_error']*2==.05
    assert client.post('/api/runs',json={'suite':'unknown'}).status_code==422


def test_policy_disagreement_stops_before_any_execution(monkeypatch):
    import app.engine as module
    monkeypatch.setattr(module,'inspect',lambda *args:{'allowed':True,'rules':[],'policy_version':'refund-v1'})
    engine=Engine(Store(':memory:'))
    run=engine.create(21004,1,suite='adversarial')
    from app.providers import ProviderError
    with pytest.raises(ProviderError,match='policy checks disagreed'):
        engine.step(run['id'],0)
    assert engine.store.events(run['id'])==[]
    assert engine.store.db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0]==0
    assert engine.store.run(run['id'])['status']=='policy_error'


def test_legacy_exports_remain_readable_without_fabricated_reviews():
    import json
    from pathlib import Path
    from fastapi.testclient import TestClient
    from app.main import create_app
    example=json.loads((Path(__file__).parents[1]/'docs/examples/claude-evaluation-20.json').read_text())
    app=create_app(':memory:',seed_demo=False)
    app.state.store.put_run(example['run'])
    for event in example['events']:app.state.store.commit_event(event)
    client=TestClient(app)
    run=example['run']['id']
    result=client.get(f'/api/runs/{run}').json()
    assert result['gross']['n']==20
    assert result['monitoring']['version']=='risk_v2'
    verified=client.get(f'/api/runs/{run}/verify').json()
    assert verified['legacy']==20 and verified['verified']==0
    assert verified['mismatches']==0


def test_benchmark_endpoint_exposes_recorded_synthetic_evidence():
    from fastapi.testclient import TestClient
    from app.main import create_app
    result=TestClient(create_app(':memory:',seed_demo=False)).get('/api/benchmarks').json()
    assert result['available']
    assert result['study']['provider_requests']==0
    assert result['study']['policy']['harmful_allowed']==0


def test_incomplete_legacy_or_changed_prompt_cannot_mix_versions(monkeypatch):
    from app.engine import Busy
    engine=Engine(Store(':memory:'))
    run=engine.create(41,3)
    run.pop('framework')
    engine.store.put_run(run)
    with pytest.raises(Busy,match='earlier workflow or prompt'):
        engine.step(run['id'],0)
    assert engine.store.events(run['id'])==[]
    run=engine.create(42,3,mode='claude')
    run['prompt_version']='earlier-prompt'
    engine.store.put_run(run)
    with pytest.raises(Busy,match='earlier workflow or prompt'):
        engine.step(run['id'],0)
    assert engine.store.attempts()==0
