import json
from datetime import datetime
from app.travel_v3 import generate, record_view, payload, outcome, context
from app.travel_factorial import payload as old_payload
from app.providers import MODELS
from scripts.verify_travel_factorial import independent_check


def test_fresh_harder_records_have_independently_checked_choices():
    cases = generate(); assert cases == generate() and len(cases) == 32
    assert sum(not c['truth']['valid_offer_ids'] for c in cases) == 8
    assert sum(len(c['truth']['valid_offer_ids']) > 1 for c in cases) == 8
    old = json.load(open('docs/examples/travel-factorial.json'))
    assert {c['observation']['authenticated_request']['trip_id'] for c in cases}.isdisjoint(c['observation']['authenticated_request']['trip_id'] for c in old['cases'])
    for c in cases:
        obs = c['observation']; view = record_view(obs)
        for q in view['current_quotes']:
            raw = obs['quotes'][q['quote_source_indices'][0]]
            assert q['total_cents'] == raw['base_cents'] + sum(raw['fee_cents'])
            assert q['deadline_minus_arrival_seconds'] == int(datetime.fromisoformat(obs['authenticated_request']['arrival_deadline']).timestamp() - datetime.fromisoformat(raw['arrival']).timestamp())
            p = {'action': 'book', 'offer_id': q['offer_id'], 'traveller_id': obs['authenticated_request']['traveller_id'], 'quoted_total_cents': q['total_cents'], 'reason': 'Independent test'}
            independent = independent_check(obs, p)
            assert (not independent['rules']) == (q['offer_id'] in c['truth']['valid_offer_ids'])
            assert q['revision'] == max(x['revision'] for x in obs['quotes'] if x['offer_id'] == q['offer_id'])
    assert any(len(q['fee_cents']) >= 40 for c in cases for q in c['observation']['quotes'])
    assert any(q['deadline_minus_arrival_seconds'] == 0 for c in cases for q in record_view(c['observation'])['current_quotes'])


def test_settings_and_schema_stay_exactly_shared_while_critic_ignores_prose():
    c = generate()[0]; obs = c['observation']; initial = {'action': 'escalate', 'offer_id': '', 'traveller_id': obs['authenticated_request']['traveller_id'], 'quoted_total_cents': 0, 'reason': 'Untrusted speculative prose'}
    for model in MODELS:
        baseline = old_payload(obs, [], model)
        for workflow in ('legacy', 'grounded'):
            r = payload(obs, [], model, initial, workflow)
            assert r['output_config'] == baseline['output_config'] and r['thinking'] == baseline['thinking'] and r['max_tokens'] == baseline['max_tokens']
            assert '"truth"' not in json.dumps(r) and 'valid_offer_ids' not in json.dumps(r)
            if workflow == 'grounded':
                parsed = json.loads(r['messages'][0]['content'])
                assert 'reason' not in parsed['untrusted_initial_proposal'] and 'current_record_arithmetic' in parsed
    a, b = [payload(obs, [], model) for model in MODELS]; a.pop('model'); b.pop('model'); assert a == b


def test_discovery_development_cases_are_separate_and_never_count_as_holdout():
    from scripts.travel_discovery import cases, request_for
    scout = cases(); heldout = generate()
    assert {c['id'] for c in scout}.isdisjoint(c['id'] for c in heldout)
    assert {c['observation']['authenticated_request']['trip_id'] for c in scout}.isdisjoint(c['observation']['authenticated_request']['trip_id'] for c in heldout)
    p = request_for([], MODELS[0]); assert p['max_tokens'] == 3072 and p['thinking']['type'] == 'adaptive'
    assert 'frequency' not in p['output_config']['format']['schema']['properties']


def test_joint_workflow_bounds_keep_pairing_missingness_and_fixed_batch_scope():
    import copy
    from tests.test_travel_factorial import fixture
    from app.travel_v3_stats import analyze
    s = fixture()
    s['cells'] = [{**copy.deepcopy(row), 'workflow': w} for w in ('legacy', 'grounded') for row in s['cells']]
    a = analyze(s)
    assert a['robust_analysis']['intervals'] == 240 and len(a['workflow_comparisons']) == 8
    import math
    radius = math.sqrt(math.log(2 * 240 / .05) / (2 * 32))
    first = next(iter(a['robust_analysis']['arms'].values()))
    assert abs(first['harm']['simultaneous95'][1] - radius) < 1e-12
    assert abs(a['robust_analysis']['comparisons'][0]['metrics']['harm']['simultaneous95'][1] - 2 * radius) < 1e-12
    for c in a['workflow_comparisons']:
        assert c['metrics']['harm']['avoided'] == c['metrics']['harm']['introduced'] == 0
        assert c['metrics']['harm']['credible95'][0] < 0 < c['metrics']['harm']['credible95'][1]
    r = s['cells'][0]
    r['initial_outcome'] = outcome(s['cases'][0], {'status': 'invalid_response'})
    audit = analyze(s)['robust_analysis']
    key = 'legacy:' + r['model'] + '|' + r['memory_mode'] + '|0'
    assert audit['arms'][key]['harm']['empirical_missing_range'] == [0, 1 / 32]
    assert audit['arms'][key]['dollars']['empirical_missing_range'] == [0, 1000 / 32]
    s['status'] = 'running'
    assert all(x['harm']['simultaneous95'] is None for x in analyze(s)['robust_analysis']['arms'].values())
