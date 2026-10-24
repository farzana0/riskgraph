"""Independently reconstruct the registered matched travel study, without API calls."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.travel_factorial import (VERSION, MODES, BANK, MAX_USD, MAX_REQUESTS, generate,
                                  select_memory, memory_context, payload, outcome, eligible)
from app.travel_factorial_stats import analyze
from app.hardcases import digest
from app.hardbench import PRICES
from app.providers import MODELS
from scripts.travel_factorial import registration
from scripts.verify_research import equivalent


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
    return {'cases': len(cases), 'configurations': 8, 'unique_requests': len(requests), 'response_ids': len(responses),
            'estimated_cost_usd': cost, 'memory_sources_and_traces_verified': True,
            'identical_model_output_format_and_settings': True, 'outcomes_and_paired_intervals_recomputed': True,
            'study_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('study', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    result = verify(a.study)
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
