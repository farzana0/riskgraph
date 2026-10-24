from copy import deepcopy
import json
import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.stats import beta
from app.domain import Case, Proposal
from app.paired_demo import (SCENARIOS, CONFIGS, WEIGHTS, PLAN, digest, generate_split,
                             replay, load_bundle, analyze, exact_upper, classify)
from app.main import create_app


@pytest.fixture(scope='module')
def bundle():
    return load_bundle()


def all_ids(bundle, split='heldout'):
    return [t['id'] for t in bundle[split]['traces']]


def test_frozen_design_and_independent_reproducible_cases(bundle):
    rows = generate_split('heldout', PLAN['heldout_seed'], 10)
    assert rows == bundle['heldout']['cases']
    assert len({r['id'] for r in rows}) == 60
    assert all(sum(r['family'] == s for r in rows) == 10 for s in SCENARIOS)
    assert {r['id'] for r in rows}.isdisjoint(r['id'] for r in bundle['development']['cases'])
    assert bundle['evidence_digest'] == digest(bundle['heldout'])
    assert generate_split('development', 123, 2) != generate_split('development', 124, 2)
    for r in rows:
        assert classify(Case(**r['case']), r['injection_tag']) == r['family']


def test_overlap_precedence(bundle):
    c = Case(**bundle['heldout']['cases'][0]['case'])
    c.order.owner = 'other'; c.order.refunded_cents = c.order.paid_cents; c.order.age_days = 45
    assert classify(c, True) == 'prompt_injection'
    assert classify(c) == 'wrong_owner'
    c.customer = 'other'
    assert classify(c) == 'duplicate_refund'
    c.order.refunded_cents = 0
    assert classify(c) == 'expired_request'


def test_paired_reuse_fresh_ledgers_and_accounting(bundle):
    before = deepcopy(bundle['heldout']['cases'])
    for r in before:
        traces = [replay(r, c) for c in CONFIGS]
        assert len({t['output_digest'] for t in traces}) == 1
        assert all(t['outcome']['ledger_before'] == traces[0]['outcome']['ledger_before'] for t in traces)
        for t in traces:
            o = t['outcome']
            delta = sum(o['ledger_after'].values()) - sum(o['ledger_before'].values())
            assert delta == o['executed_cents']
            assert isinstance(o['exposure_cents'], int)
            if o['blocked'] or o['escalated']:
                assert delta == o['exposure_cents'] == 0
        assert traces == [replay(r, c) for c in CONFIGS]  # No carryover on replay.
    assert bundle['heldout']['cases'] == before
    assert any(replay(r, 'none')['outcome']['exposure_cents'] > 0 for r in before)
    assert all(replay(r, 'rules')['outcome']['exposure_cents'] == 0 for r in before)
    assert any(replay(r, 'none')['outcome']['legitimate_completed'] and not replay(r, 'reviewer')['outcome']['legitimate_completed'] for r in bundle['walkthrough']['cases'])
    assert digest(bundle['heldout']) == '35f0061efc19cffaf55e81711f970b3008188884cab2f31a97082b3a09071b26'


def test_prior_zero_all_failures_and_beta_updates(bundle):
    empty = analyze(bundle, [])
    for c in CONFIGS:
        for cell in empty['cells'][c].values():
            assert cell['prior_only'] and cell['n'] == cell['k'] == 0
            assert cell['empirical'] is None and cell['exact_upper'] == 1
            assert cell['posterior_mean'] == .5
            assert cell['credible95'] == pytest.approx([.025, .975])
    ids = all_ids(bundle)
    result = analyze(bundle, ids, a=2, b=3)
    for c in CONFIGS:
        for cell in result['cells'][c].values():
            n, k = cell['n'], cell['k']
            assert n == 10
            assert cell['posterior_mean'] == pytest.approx((2+k)/(5+n))
            assert cell['credible95'] == pytest.approx(beta.ppf([.025,.975],2+k,3+n-k))
    allfail = deepcopy(bundle)
    for t in allfail['heldout']['traces']:
        t['outcome']['unauthorized'] = True
    cell = analyze(allfail, ids)['cells']['none']['normal']
    assert cell['k'] == cell['n'] and cell['exact_upper'] == 1
    zero = result['cells']['rules']['normal']
    assert zero['k'] == 0 and zero['posterior_mean'] > 0


def test_exact_bound_independent_reference_and_family_correction():
    assert exact_upper(0, 60, .05) == pytest.approx(.0487029133, abs=1e-10)
    assert exact_upper(0, 60, .05) == pytest.approx(1-.05**(1/60))
    assert exact_upper(0, 10) == pytest.approx(1-(.05/24)**.1)
    assert exact_upper(4, 10) == pytest.approx(beta.ppf(1-.05/24,5,6))
    assert exact_upper(10,10) == exact_upper(0,0) == 1
    assert 24*(.05/24) == pytest.approx(.05)
    for k,n,a in [(-1,10,.05),(11,10,.05),(0,-1,.05),(0,10,0)]:
        with pytest.raises(ValueError):exact_upper(k,n,a)


def test_projection_weights_independent_draws_and_money(bundle):
    ids = all_ids(bundle)
    baseline = analyze(bundle, ids)
    assert baseline == analyze(bundle, ids)
    weight = {s: float(s == 'normal') for s in SCENARIOS}
    changed = analyze(bundle, ids, weight)
    assert changed['cells'] == baseline['cells']
    for c in CONFIGS:
        p, cell = changed['projections'][c], changed['cells'][c]['normal']
        assert p['posterior_mean'] == cell['posterior_mean']
        assert p['empirical'] == cell['empirical']
        assert p['mean_exposure_cents'] == cell['mean_exposure_cents']
        assert p['exact_upper'] == cell['exact_upper']
        assert p['credible95'] == pytest.approx(cell['credible95'], abs=.008)
    p = baseline['projections']['none']
    assert p['exact_upper'] == pytest.approx(sum(WEIGHTS[s]*baseline['cells']['none'][s]['exact_upper'] for s in SCENARIOS))
    assert p['mean_exposure_cents'] == pytest.approx(sum(WEIGHTS[s]*baseline['cells']['none'][s]['exposure_cents']/10 for s in SCENARIOS))
    for w in [{}, {**WEIGHTS,'normal':-.1}, {**WEIGHTS,'normal':.6}, {**WEIGHTS,'normal':float('nan')}]:
        with pytest.raises(ValueError):analyze(bundle, ids, w)
    for a in [0,-1,float('inf'),101]:
        with pytest.raises(ValueError):analyze(bundle, ids, a=a)


def test_missing_errors_streaming_and_idempotence(bundle):
    ids = all_ids(bundle)
    assert analyze(bundle, ids)['batch_complete']
    incomplete = analyze(bundle, ids[:-1])
    assert not incomplete['batch_complete']
    assert all(p['exact_upper'] is None for p in incomplete['projections'].values())
    assert analyze(bundle, ids[:4]+ids[:4]) == analyze(bundle, ids[:4])
    assert analyze(bundle, ids[:4])['unique_cases'] == 1
    error_bundle = deepcopy(bundle)
    r = next(r for r in error_bundle['heldout']['cases'] if r['proposal']['action'] == 'refund')
    failed = replay(r, 'none', payment_error=True)
    error_bundle['heldout']['traces'] = [failed if t['id']==failed['id'] else t for t in error_bundle['heldout']['traces']]
    result = analyze(error_bundle, ids)
    cell = result['cells']['none'][r['family']]
    assert not result['batch_complete'] and cell['n'] == 9 and cell['execution_errors'] == 1 and cell['unresolved'] == 1
    assert failed['outcome']['exposure_cents'] is None
    assert result['projections']['none']['exact_upper'] is None
    with pytest.raises(ValueError):analyze(bundle,['unknown'])


def test_archived_real_not_mixed_or_treated_as_iid_study(bundle):
    result = analyze(bundle, all_ids(bundle,'recorded'), split='recorded')
    assert result['unique_cases'] == 3 and result['batch_complete']
    assert all(p['exact_upper'] is None and p['empirical'] is None for p in result['projections'].values())
    assert any(c['prior_only'] for c in result['cells']['none'].values())
    assert 'archive' in result['bound_status']
    assert all(t['case_id'].startswith('recorded-') for t in bundle['recorded']['traces'])


def test_saved_graph_events_and_api(bundle):
    for t in bundle['heldout']['traces']:
        assert t['events'][0]['node']=='request' and t['events'][-1]['node']=='evaluator'
        for a,b in zip(t['events'],t['events'][1:]):
            assert b['from']==a['node']
        assert len({e['id'] for e in t['events']}) == len(t['events'])
        assert (any(e['node']=='payment' for e in t['events'])) == (t['outcome']['executed_cents']>0)
    client = TestClient(create_app(':memory:',seed_demo=False))
    assert client.get('/demo').status_code == 200
    assert client.get('/static/demo.js').status_code == 200
    assert client.get('/api/paired-demo').json()['evidence_digest']==bundle['evidence_digest']
    body = {'admitted_ids':all_ids(bundle),'weights':WEIGHTS}
    assert client.post('/api/paired-demo/analyze',json=body).json()['batch_complete']
    assert client.post('/api/paired-demo/analyze',json={**body,'admitted_ids':['invalid']}).status_code==422


def test_curated_fault_stays_unresolved_and_recorded_outputs_are_authentic(bundle):
    from app.paired_demo import BUNDLE
    result = analyze(bundle, all_ids(bundle, 'walkthrough'), split='walkthrough')
    assert result['execution_errors'] == 4
    assert result['completed_outcomes'] == 8 and result['admitted_outcomes'] == 12
    assert result['missing_outcomes'] == 0 and not result['batch_complete']
    assert all(p['exact_upper'] is None for p in result['projections'].values())
    archive = json.loads((BUNDLE.parent / 'two-model-memory-smoke.json').read_text())
    for row, source in zip(bundle['recorded']['cases'], archive['events']):
        assert row['proposal'] == source['proposal']
        assert row['reviewer']['reason'] == source['critique']['reason']
        assert row['reviewer']['verdict'] == ('approve' if source['critique']['recommendation']=='accept' else 'escalate')
    assert bundle['heldout']['traces'] == [replay(r,c) for r in bundle['heldout']['cases'] for c in CONFIGS]
