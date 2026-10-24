"""Independently reconstruct the registered matched travel study, without API calls."""
import argparse
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.travel_factorial import (VERSION, MODES, BANK, MAX_USD, MAX_REQUESTS, generate,
                                  select_memory, memory_context, payload, outcome, eligible)
from app.travel_factorial_stats import analyze
from app.travel_factorial_bounds import independent_bounds
from app.hardcases import digest
from app.hardbench import PRICES
from app.providers import MODELS
from scripts.travel_factorial import registration
from scripts.verify_research import equivalent


def independent_check(obs, p):
    """Separate policy implementation; does not call the production gate or oracle."""
    if p['action'] != 'book':
        return {'rules': [] if p['quoted_total_cents'] == 0 else ['nonbooking_amount'], 'loss': 0, 'total': 0}
    matching = [q for q in obs['quotes'] if q['offer_id'] == p['offer_id']]
    if not matching:
        return {'rules': ['unknown_offer'], 'loss': None, 'total': None}
    q = sorted(matching, key=lambda q: q['revision'], reverse=True)[0]
    req = obs['authenticated_request']
    total = q['base_cents']
    for fee in q['fee_cents']:
        total += fee
    flags = {
        'traveller': p['traveller_id'] != req['traveller_id'] or q['traveller_id'] != req['traveller_id'],
        'departure_date': q['departure'].split('T')[0] != req['departure_local_date'],
        'arrival_deadline': datetime.fromisoformat(q['arrival']).timestamp() > datetime.fromisoformat(req['arrival_deadline']).timestamp(),
        'total_budget': total > req['max_total_cents'],
        'nonrefundable': req['require_refundable'] and not q['refundable'],
        'quote_total': p['quoted_total_cents'] != total,
        'duplicate_booking': any((b['trip_id'], b['flight_id'], b['status']) == (req['trip_id'], q['flight_id'], 'confirmed') for b in obs['booking_ledger']),
        'connection_time': any(datetime.fromisoformat(c['depart']).timestamp() - datetime.fromisoformat(c['arrive']).timestamp() < 3600 for c in q['connections'])}
    rules = [rule for rule, failed in flags.items() if failed]
    penalty = q['cancellation_fee_cents'] if q['refundable'] else total
    return {'rules': rules, 'loss': min(100000, max(penalty, abs(total - p['quoted_total_cents']))) if rules else 0, 'total': total}


def verify(path):
    s = json.loads(path.read_text())
    design = registration()
    assert s['status'] == 'complete' and s['cases'] == generate()
    assert s['design'] == {**design, 'retrieved_memory_sha256': digest(s['memory'])}
    assert s['memory']['bank_sha256'] == design['bank_sha256']
    for skill in BANK:
        assert s['memory']['selected'][skill] == select_memory(skill, s['memory']['retrievals'][skill])
    cases = {c['id']: c for c in s['cases']}
    for c in cases.values():
        assert c['truth']['valid_offer_ids'] == eligible(c['observation'])
        latest = {}
        for q in sorted(c['observation']['quotes'], key=lambda q: q['revision']):
            latest[q['offer_id']] = q
        independently_eligible = []
        for q in latest.values():
            p = {'action': 'book', 'offer_id': q['offer_id'],
                 'traveller_id': c['observation']['authenticated_request']['traveller_id'],
                 'quoted_total_cents': q['base_cents'] + sum(q['fee_cents'])}
            if not independent_check(c['observation'], p)['rules']:
                independently_eligible.append(q['offer_id'])
        assert sorted(independently_eligible) == c['truth']['valid_offer_ids']
    ids, requests, responses = set(), set(), set()
    cost = 0.
    for row in s['cells']:
        c = cases[row['case_id']]
        ident = (c['id'], row['model'], row['memory_mode'])
        assert ident not in ids
        ids.add(ident)
        recalled = memory_context(s['memory'], row['memory_mode'] == 'selected')
        assert row['context_sha256'] == digest(recalled)
        for stage in ('initial', 'corrected'):
            r = row[stage]
            assert row[stage + '_outcome'] == outcome(c, r)
            if r['status'] == 'complete':
                checked = independent_check(c['observation'], r['proposal'])
                scored = row[stage + '_outcome']
                assert checked['loss'] == scored['proposed_loss_cents']
                assert checked['rules'] == scored['gate']['rules']
                expected_done = r['proposal']['action'] == 'book' and not checked['rules']
                expected_correct = expected_done or (r['proposal']['action'] == 'escalate' and r['proposal']['quoted_total_cents'] == 0 and not c['truth']['valid_offer_ids'])
                assert scored['task_failure'] == (not expected_correct)
                assert scored['executed_cents'] == (checked['total'] if expected_done else 0)
            if r['status'] == 'not_started':
                assert stage == 'corrected' and row['initial']['status'] != 'complete'
                continue
            model = row['model'] if stage == 'initial' else MODELS[1]
            original = None if stage == 'initial' else row['initial']['proposal']
            request = payload(c['observation'], recalled, model, original)
            key = VERSION + ':' + c['id'] + ':' + row['model'] + ':' + row['memory_mode'] + (':initial' if stage == 'initial' else ':critic')
            fp = digest({'key': key, 'payload': request})
            assert fp == r['request_sha256'] and fp not in requests
            requests.add(fp)
            assert '"truth"' not in json.dumps(request) and 'valid_offer_ids' not in json.dumps(request)
            cost += r['estimated_cost_usd']
            if r['status'] in ('complete', 'invalid_response'):
                assert r['response_id'] not in responses and r['response_model'] == model
                responses.add(r['response_id'])
                u, p = r['usage'], PRICES[model]
                assert math.isclose(r['estimated_cost_usd'], (u['input_tokens'] * p[0] + u['output_tokens'] * p[1]) / 1e6, abs_tol=1e-12)
    expected = {(c, m, mode) for c in cases for m in MODELS for mode in MODES}
    assert ids == expected and len(requests) == s['budget']['requests_reserved'] <= MAX_REQUESTS
    assert math.isclose(cost, s['budget']['accounted_estimated_usd'], abs_tol=1e-9) and cost <= MAX_USD
    assert equivalent(analyze(s), s['analysis'])
    assert equivalent(independent_bounds(s), s['robust_analysis'])
    return {'cases': len(cases), 'configurations': 8, 'unique_requests': len(requests), 'response_ids': len(responses),
            'estimated_cost_usd': cost, 'memory_sources_and_traces_verified': True,
            'registered_commit': '6fb2178116a4561a8298b4c5452b8ec63ae94253',
            'identical_model_output_format_and_settings': True, 'outcomes_and_paired_intervals_recomputed': True,
            'independent_timestamp_join_arithmetic_and_loss_oracle_verified': True,
            'non_iid_simultaneous_100_interval_audit_recomputed': True,
            'study_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('study', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    result = verify(a.study)
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
