import copy
import json
import pytest
from app.travel_factorial import (generate, eligible, payload, outcome, select_memory, fact_text, BANK,
                                  MAX_TOKENS, MODES, call)
from app.travel_factorial_stats import analyze, contrasts, key
from app.providers import MODELS, Agent
from app.live_budget import LiveBudget
import httpx


def oracle(case):
    obs = case['observation']
    ids = case['truth']['valid_offer_ids']
    q = next((q for q in obs['quotes'] if ids and q['offer_id'] == ids[0] and q['revision'] == 3), None)
    return {'status': 'complete', 'proposal': {'action': 'book' if ids else 'escalate',
            'offer_id': ids[0] if ids else '', 'traveller_id': obs['authenticated_request']['traveller_id'],
            'quoted_total_cents': q['base_cents'] + sum(q['fee_cents']) if q else 0, 'reason': 'Offline scoring test'}}


def fixture():
    cases = generate()
    rows = []
    for c in cases:
        r = oracle(c)
        for model in MODELS:
            for mode in MODES:
                rows.append({'case_id': c['id'], 'family': c['family'], 'model': model, 'memory_mode': mode,
                             'initial_outcome': outcome(c, r), 'corrected_outcome': outcome(c, r)})
    return {'status': 'complete', 'cases': cases, 'cells': rows}


def test_common_interface_and_fresh_no_choice_controls():
    from scripts.travel_factorial import registration
    design = registration()
    assert json.loads(json.dumps(design)) == design
    cases = generate()
    assert cases == generate() and len(cases) == 32
    assert sum(not c['truth']['valid_offer_ids'] for c in cases) == 8
    old = json.load(open('docs/examples/travel-v1.json'))
    assert {c['observation']['authenticated_request']['trip_id'] for c in cases}.isdisjoint(c['observation']['authenticated_request']['trip_id'] for c in old['cases'])
    for c in cases:
        assert eligible(c['observation']) == c['truth']['valid_offer_ids']
        assert not outcome(c, oracle(c))['task_failure']
        assert all(len(q['offer_id']) == 18 for q in c['observation']['quotes'])
        a, b = [payload(c['observation'], [], model) for model in MODELS]
        a.pop('model'); b.pop('model')
        assert a == b and a['max_tokens'] == MAX_TOKENS and a['thinking'] == {'type': 'adaptive'}
        assert a['output_config']['format']['type'] == 'json_schema' and 'tools' not in a
        assert 'truth' not in json.dumps(a) and 'valid_offer_ids' not in json.dumps(a)


def test_hosted_memory_rejects_wrong_content_or_missing_provenance():
    for skill in BANK:
        response = {'hits': [{'id': 'fact-1', 'text': fact_text(skill)}], 'trace': {'traceId': 'trace-1'}}
        assert select_memory(skill, response)['authority'] == 'procedural_advice_only'
        for bad in ({**response, 'trace': {}}, {**response, 'hits': [{'id': 'fact-1', 'text': 'unverified advice'}]}):
            with pytest.raises(ValueError): select_memory(skill, bad)


def test_paired_intervals_do_not_manufacture_benefit_or_replace_missing_loss():
    s = fixture()
    a = analyze(s)
    assert len(a['arms']) == 8 and len(a['comparisons']) == len(contrasts()) == 12
    for comparison in a['comparisons']:
        for metric in comparison['metrics'].values():
            assert metric['posterior_reduction'] == 0
            assert metric['credible95'][0] < 0 < metric['credible95'][1]
            assert metric['avoided'] == metric['introduced'] == 0
    s['cells'][0]['initial_outcome'] = outcome(s['cases'][0], {'status': 'invalid_response'})
    a = analyze(s)
    arm = a['arms'][key(s['cells'][0]['model'], s['cells'][0]['memory_mode'], False)]
    assert arm['unresolved'] == 1 and arm['metrics']['harm']['confidence95'] is None
    assert arm['mean_loss_missing_range_usd'] == [0, 1000 / 32]
    assert arm['metrics']['adverse']['counts'][s['cases'][0]['family']]['k'] == 1
    assert arm['metrics']['harm']['counts'][s['cases'][0]['family']]['unknown'] == 1
    assert arm['residual_loss_usd'] == 0


def test_critic_effect_counts_fixed_and_introduced_errors_on_same_cases():
    s = fixture()
    row = next(r for r in s['cells'] if r['model'] == MODELS[0] and r['memory_mode'] == 'none')
    c = next(c for c in s['cases'] if c['id'] == row['case_id'])
    bad = copy.deepcopy(oracle(c));bad['proposal']['quoted_total_cents'] += 1
    row['initial_outcome'] = outcome(c, bad)
    a = analyze(s)
    effect = next(r for r in a['comparisons'] if r['before'] == key(MODELS[0], 'none', False) and r['after'] == key(MODELS[0], 'none', True))['metrics']['harm']
    assert effect['avoided'] == 1 and effect['introduced'] == 0 and effect['resolved_pairs'] == 32
    assert effect['posterior_reduction'] > 0 and effect['credible95'][0] < 0


def test_structured_call_is_metered_cached_and_incomplete_stays_unknown(tmp_path, monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-only')
    monkeypatch.setenv('ANTHROPIC_WORKSPACE_ID', 'test-workspace')
    c = generate()[0];proposal = oracle(c)['proposal'];seen = []
    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={'id': 'response-1', 'model': MODELS[0], 'stop_reason': 'end_turn',
                'usage': {'input_tokens': 500, 'output_tokens': 100},
                'content': [{'type': 'text', 'text': json.dumps(proposal)}]})
    agent = Agent(httpx.Client(transport=httpx.MockTransport(handler)))
    budget = LiveBudget(tmp_path / 'calls.sqlite3', .1, 2)
    request = payload(c['observation'], [], MODELS[0])
    r = call(agent, budget, request, 'same-key')
    assert r['status'] == 'complete' and r['estimated_cost_usd'] == pytest.approx(.0001)
    assert call(agent, budget, request, 'same-key') == r and len(seen) == 1
    assert budget.totals()['requests_reserved'] == 1
    def incomplete(request):
        return httpx.Response(200, json={'id': 'response-2', 'model': MODELS[0], 'stop_reason': 'max_tokens',
                'usage': {'input_tokens': 500, 'output_tokens': 1536},
                'content': [{'type': 'text', 'text': '{"action":'}]})
    bad_agent = Agent(httpx.Client(transport=httpx.MockTransport(incomplete)))
    bad = call(bad_agent, budget, request, 'incomplete-key')
    assert bad['status'] == 'invalid_response'
    assert outcome(c, bad)['proposed_loss_cents'] is None and outcome(c, bad)['executed_cents'] == 0
    with pytest.raises(RuntimeError): call(agent, budget, request, 'over-request-limit')
    assert budget.totals()['requests_reserved'] == 2
    budget.db.close()


def test_matched_routes_are_public_read_only_with_no_provider_calls(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from app.main import create_app
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'service.sqlite3'))
    client = TestClient(create_app(':memory:', seed_demo=False))
    page = client.get('/travel/compare')
    assert page.status_code == 200 and 'travel-compare.js' in page.text
    assert client.get('/api/travel-factorial').status_code == 200
    assert client.post('/api/travel-factorial', json={}).status_code == 405
    assert 'script-src' in page.headers['content-security-policy']


def test_non_iid_quota_bounds_cover_pairs_and_preserve_unknown_ranges():
    from app.travel_factorial_bounds import independent_bounds
    s = fixture()
    b = independent_bounds(s)
    assert b['intervals'] == 100 and b['joint_confidence'] == .95
    arm = key(MODELS[0], 'none', False)
    assert b['arms'][arm]['harm']['empirical_missing_range'] == [0, 0]
    assert b['arms'][arm]['harm']['simultaneous95'][0] == 0
    assert all(r['metrics']['harm']['simultaneous95'][0] < 0 < r['metrics']['harm']['simultaneous95'][1] for r in b['comparisons'])
    s['cells'][0]['initial_outcome'] = outcome(s['cases'][0], {'status': 'invalid_response'})
    b = independent_bounds(s)
    assert b['arms'][arm]['harm']['empirical_missing_range'] == [0, 1 / 32]
    assert b['arms'][arm]['dollars']['empirical_missing_range'] == [0, 1000 / 32]
    s['status'] = 'running'
    assert independent_bounds(s)['arms'][arm]['harm']['simultaneous95'] is None


def test_committed_real_study_reconstructs_without_any_provider_call():
    from pathlib import Path
    from scripts.verify_travel_factorial import verify
    root = Path(__file__).resolve().parents[1]
    report = verify(root / 'docs/examples/travel-factorial.json')
    expected = json.loads((root / 'docs/examples/travel-factorial-verification.json').read_text())
    assert report == expected and report['unique_requests'] == 256
