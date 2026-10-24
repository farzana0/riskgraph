"""Rebuild the prospective record-grounding study from archived real responses."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.hardcases import digest
from app.hardbench import PRICES
from app.providers import MODELS
from app.travel_v3 import VERSION, WORKFLOWS, BANK, generate, context, payload, outcome, record_view, select_memory
from app.travel_v3_stats import analyze
from scripts.travel_v3 import registration, MAX_USD
from scripts.verify_travel_factorial import independent_check
from scripts.verify_research import equivalent


def check_case(c):
    obs = c['observation']; latest = {}
    for q in sorted(obs['quotes'], key=lambda x: x['revision']): latest[q['offer_id']] = q
    valid = []
    for q in latest.values():
        p = {'action': 'book', 'offer_id': q['offer_id'], 'traveller_id': obs['authenticated_request']['traveller_id'],
             'quoted_total_cents': q['base_cents'] + sum(q['fee_cents'])}
        if not independent_check(obs, p)['rules']: valid.append(q['offer_id'])
    assert sorted(valid) == c['truth']['valid_offer_ids']


def check_outcome(c, call, scored):
    assert scored == outcome(c, call)
    if call['status'] != 'complete': return
    p = call['proposal']; checked = independent_check(c['observation'], p)
    assert checked['loss'] == scored['proposed_loss_cents'] and checked['rules'] == scored['gate']['rules']
    done = p['action'] == 'book' and not checked['rules']
    correct = done or (p['action'] == 'escalate' and p['quoted_total_cents'] == 0 and not c['truth']['valid_offer_ids'])
    assert scored['task_failure'] == (not correct)
    assert scored['executed_cents'] == (checked['total'] if done else 0)


def check_call(r, request, key, seen, responses):
    fp = digest({'key': key, 'payload': request})
    assert fp == r['request_sha256'] and fp not in seen; seen.add(fp)
    assert 'valid_offer_ids' not in json.dumps(request) and '"truth"' not in json.dumps(request)
    assert r['status'] in ('complete', 'invalid_response'), 'A completed replication must retain provider failures explicitly'
    assert r['response_id'] not in responses and r['response_model'] == request['model']; responses.add(r['response_id'])
    u, p = r['usage'], PRICES[request['model']]
    cost = (u['input_tokens'] * p[0] + u['output_tokens'] * p[1]) / 1e6
    assert math.isclose(cost, r['estimated_cost_usd'], abs_tol=1e-12)
    return cost


def verify(path):
    s = json.loads(path.read_text()); design = registration()
    assert s['status'] == 'complete' and s['processed_cases'] == 32 and s['cases'] == generate()
    assert s['design'] == {**design, 'retrieved_memory_sha256': digest(s['memory'])}
    assert s['memory']['bank_sha256'] == design['bank_sha256']
    old = json.loads((Path(__file__).resolve().parents[1] / 'docs/examples/travel-factorial.json').read_text())
    assert s['memory']['legacy'] == old['memory']
    for skill in BANK:
        bank = s['memory']['grounded']
        assert bank['selected'][skill] == select_memory(skill, bank['retrievals'][skill])
        assert bank['write_turn_ids'][skill]
    cases = {c['id']: c for c in s['cases']}
    for c in cases.values(): check_case(c)
    identities, requests, responses = set(), set(), set(); cost = 0
    for row in s['cells']:
        c = cases[row['case_id']]; w = row['workflow']
        ident = (c['id'], row['model'], row['memory_mode'], w)
        assert ident not in identities; identities.add(ident)
        memories = context(s['memory'], row['memory_mode'] == 'selected', w)
        assert row['context_sha256'] == digest(memories)
        assert row['record_view_sha256'] == (digest(record_view(c['observation'])) if w == 'grounded' else None)
        for stage in ('initial', 'corrected'):
            r = row[stage]; check_outcome(c, r, row[stage + '_outcome'])
            if r['status'] == 'not_started':
                assert stage == 'corrected' and row['initial']['status'] != 'complete'; continue
            model = row['model'] if stage == 'initial' else MODELS[1]
            original = None if stage == 'initial' else row['initial']['proposal']
            request = payload(c['observation'], memories, model, original, w)
            assert request['max_tokens'] == 1536 and request['thinking'] == {'type': 'adaptive'}
            assert request['output_config']['effort'] == 'low'
            key = VERSION + ':' + c['id'] + ':' + row['model'] + ':' + row['memory_mode'] + ':' + w + (':initial' if stage == 'initial' else ':critic')
            cost += check_call(r, request, key, requests, responses)
    assert identities == {(c, m, mode, w) for c in cases for m in MODELS for mode in ('none', 'selected') for w in WORKFLOWS}
    assert len(requests) == s['budget']['requests_reserved'] <= 512
    assert math.isclose(cost, s['budget']['accounted_estimated_usd'], abs_tol=1e-9) and cost <= MAX_USD
    rebuilt = analyze(s)
    for field in rebuilt: assert equivalent(rebuilt[field], s[field]), field
    assert rebuilt['robust_analysis']['intervals'] == 240
    return {'cases': len(cases), 'configurations': 16, 'unique_requests': len(requests), 'response_ids': len(responses),
            'estimated_cost_usd': cost, 'registered_commit': '56504f0160f7e1fde5573ea437fff3ee72d6ffb9',
            'same_settings_and_output_schema': True, 'independent_gate_loss_and_eligibility_rebuilt': True,
            'memory_sources_and_context_digests_rebuilt': True, 'all_paired_posteriors_and_240_simultaneous_bounds_rebuilt': True,
            'study_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def verify_discovery(path):
    from scripts.travel_discovery import cases, registration, request_for, VERSION
    from app.travel_factorial import payload as raw_payload
    s = json.loads(path.read_text())
    assert s['status'] == 'complete' and s['design'] == registration() and s['cases'] == cases()
    cs = {c['id']: c for c in s['cases']}
    assert set(cs).isdisjoint(c['id'] for c in generate())
    requests, responses, identities = set(), set(), set(); cost = 0
    for row in s['scouts']:
        c = cs[row['case_id']]; ident = (c['id'], row['model'])
        assert ident not in identities; identities.add(ident); check_case(c)
        check_outcome(c, row['call'], row['outcome'])
        cost += check_call(row['call'], raw_payload(c['observation'], [], row['model']), VERSION + ':' + c['id'] + ':' + row['model'], requests, responses)
    assert identities == {(c, m) for c in cs for m in MODELS}
    corpus = [{'case_id': r['case_id'], 'model': r['model'], 'records': cs[r['case_id']]['observation'],
               'proposal': r['call'].get('proposal'), 'scored_outcome': r['outcome']} for r in s['scouts']]
    assert s['corpus_sha256'] == digest(corpus)
    failed = {r['case_id'] for r in s['scouts'] if r['outcome']['task_failure']}
    assert {d['call']['model'] for d in s['discoveries']} == set(MODELS)
    labels = {'Observed trace cited': 0, 'Untested hypothesis': 0}
    for d in s['discoveries']:
        r = d['call']; cost += check_call(r, request_for(corpus, r['model']), VERSION + ':' + r['model'], requests, responses)
        assert len(d['candidates']) <= 6
        assert [{k: v for k, v in c.items() if k not in ('evidence_label', 'known_source_ids_only')} for c in d['candidates']] == r['output']['candidates']
        for c in d['candidates']:
            cited = set(c['evidence_case_ids'])
            label = 'Observed trace cited' if c['status'] == 'observed' and cited and cited <= set(cs) and cited & failed else 'Untested hypothesis'
            assert c['evidence_label'] == label and c['known_source_ids_only'] == (cited <= set(cs))
            labels[label] += 1
    assert len(requests) == s['budget']['requests_reserved'] == 10
    assert math.isclose(cost, s['budget']['accounted_estimated_usd'], abs_tol=1e-9) and cost <= .5
    return {'development_cases': 4, 'scout_calls': 8, 'discovery_calls': 2, 'estimated_cost_usd': cost,
            'candidate_labels': labels, 'request_usage_source_citations_and_labels_rebuilt': True,
            'excluded_from_heldout_sample': True, 'study_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('study', type=Path); p.add_argument('--discovery', action='store_true'); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); result = (verify_discovery if a.discovery else verify)(a.study)
    a.output.write_text(json.dumps(result, indent=2) + '\n'); print(json.dumps(result, indent=2))
