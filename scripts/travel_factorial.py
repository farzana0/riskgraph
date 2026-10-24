"""Pre-register and execute one capped, complete-block travel factorial study."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import httpx
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.travel_factorial import (VERSION, SEED, MAX_USD, MAX_REQUESTS, MAX_TOKENS, BANK, MODES, TAG,
                                  generate, entry, fact_text, select_memory, memory_context, payload, call, outcome)
from app.travel_factorial_stats import analyze
from app.hardcases import digest
from app.hardbench import PRICES
from app.live_budget import LiveBudget
from app.providers import Agent, AgentMemory, MODELS
from scripts.hard_benchmark import write

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['app/travel_factorial.py', 'app/travel_factorial_stats.py', 'scripts/travel_factorial.py',
           'app/travel.py', 'app/travel_calls.py', 'app/live_budget.py', 'app/hardbench.py',
           'app/hardcases.py', 'app/providers.py', 'app/research_stats.py']


def registration():
    cases = generate()
    return {'version': VERSION, 'seed': SEED, 'cases': len(cases), 'cases_sha256': digest(cases),
            'models': list(MODELS), 'critic_model': MODELS[1], 'memory_modes': list(MODES),
            'max_usd': MAX_USD, 'max_requests': MAX_REQUESTS,
            'settings': {'max_tokens': MAX_TOKENS, 'thinking': 'adaptive', 'effort': 'low', 'output': 'one common JSON schema; no tools'},
            'bank_sha256': digest({s: entry(s) for s in BANK}), 'ordering_seed': 20261024117,
            'price_basis_usd_per_million': {m: list(p) for m, p in PRICES.items()},
            'source_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES},
            'scope': '32 fresh opaque-ID trips; four per eight families, including eight no-eligible-offer controls. All eight model/memory/critic configurations share cases, JSON schema, adaptive thinking, low effort and token limit. Critic off reuses the exact initial proposal. The separate reviewer is always Sonnet, sees the same memory condition, and gets no gate/oracle result. Bank is frozen before calls; no online memory updates. No paid retries or outcome-driven case selection. Incomplete output is an operational error and unknown financial loss. Fixed 32-case target or hard US$3 stop, never extended based on effects. No pooling with earlier studies.'}


def freeze(directory):
    path = directory / 'memory.json'
    bank_hash = registration()['bank_sha256']
    if path.exists():
        saved = json.loads(path.read_text())
        if saved['bank_sha256'] != bank_hash or set(saved['selected']) != set(BANK):
            raise ValueError('Memory snapshot incomplete or changed')
        for skill, selected in saved['selected'].items():
            assert selected == select_memory(skill, saved['retrievals'][skill])
        return saved
    memory = AgentMemory()
    if not memory.configured:
        raise RuntimeError('Actual hosted Agent Memory is required; no local fallback')
    saved = {'bank_sha256': bank_hash, 'selected': {}, 'retrievals': {}, 'write_turn_ids': {}}
    for skill in BANK:
        stored = memory._post('/facts', {'text': fact_text(skill), 'infer': 'full', 'scopes': [[memory.scope]]}, TAG + '-' + skill)
        response = memory._post('/query', {'query': TAG + ' ' + skill + ' ' + digest(entry(skill)),
                                           'k': 8, 'lens': [[memory.scope]], 'scopeView': 'strict', 'mode': 'hybrid'})
        # Only synthetic advice and provenance are retained; no key, endpoint or scope exported.
        clean = {'hits': [{'id': h.get('id'), 'text': str(h.get('text', ''))} for h in response.get('hits', [])
                          if TAG in str(h.get('text', ''))], 'trace': {'traceId': response.get('trace', {}).get('traceId')}}
        saved['retrievals'][skill] = clean
        saved['selected'][skill] = select_memory(skill, clean)
        saved['write_turn_ids'][skill] = stored.get('turnId')
    write(path, saved)
    return saved


def execute(directory, c, model, mode, memory):
    budget = LiveBudget(directory / 'requests.sqlite3', MAX_USD, MAX_REQUESTS)
    client = httpx.Client(timeout=90)
    try:
        agent = Agent(client)
        context = memory_context(memory, mode == 'selected')
        k = VERSION + ':' + c['id'] + ':' + model + ':' + mode
        try:
            initial = call(agent, budget, payload(c['observation'], context, model), k + ':initial')
        except RuntimeError:
            initial = {'status': 'not_started', 'code': 'budget_or_unknown'}
        try:
            corrected = call(agent, budget, payload(c['observation'], context, MODELS[1], initial['proposal']), k + ':critic') if initial['status'] == 'complete' else {'status': 'not_started', 'code': 'initial_proposal_unavailable'}
        except RuntimeError:
            corrected = {'status': 'not_started', 'code': 'budget_or_unknown'}
        return {'case_id': c['id'], 'family': c['family'], 'model': model, 'memory_mode': mode,
                'context_sha256': digest(context), 'initial': initial, 'corrected': corrected,
                'initial_outcome': outcome(c, initial), 'corrected_outcome': outcome(c, corrected)}
    finally:
        budget.db.close()
        client.close()


def run(directory):
    if not os.getenv('ANTHROPIC_API_KEY'):
        raise RuntimeError('Provider not configured')
    directory.mkdir(parents=True, exist_ok=True)
    lock = (directory / 'study.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    design = registration()
    assert design == json.loads((ROOT / 'docs/examples/travel-factorial-preregistration.json').read_text())
    memory = freeze(directory)
    design = {**design, 'retrieved_memory_sha256': digest(memory)}
    budget = LiveBudget(directory / 'requests.sqlite3', MAX_USD, MAX_REQUESTS)
    budget.pin(design)
    cases = generate()
    s = {'schema_version': VERSION, 'design': design, 'memory': memory, 'cases': cases, 'cells': [],
         'status': 'running', 'budget': budget.totals()}
    path = directory / 'study.json'
    write(path, s)
    try:
        with ThreadPoolExecutor(4) as pool:
            for index, c in enumerate(cases):
                arms = [(m, mode) for m in MODELS for mode in MODES]
                random.Random(20261024117 + index).shuffle(arms)
                s['cells'].extend(pool.map(lambda arm: execute(directory, c, *arm, memory), arms))
                s['budget'] = budget.totals()
                # Analysis uses the processed prefix, avoiding uncollected rows as fake observations.
                processed = {r['case_id'] for r in s['cells']}
                s['analysis'] = analyze({**s, 'cases': [x for x in cases if x['id'] in processed]})
                write(path, s)
                print(json.dumps({'case': index + 1, 'scheduled': len(cases), 'budget': s['budget']}), flush=True)
                calls = [r[t] for r in s['cells'] for t in ('initial', 'corrected')]
                if any(x['status'] == 'provider_error' for x in calls):
                    s['status'] = 'provider_error'
                    break
                if any(x.get('code') == 'budget_or_unknown' for x in calls):
                    s['status'] = 'budget_limited'
                    break
            else:
                s['status'] = 'complete'
        processed = {r['case_id'] for r in s['cells']}
        s['analysis'] = analyze({**s, 'cases': [c for c in cases if c['id'] in processed]})
        s['processed_cases'] = len(processed)
        s['budget'] = budget.totals()
        write(path, s)
    finally:
        budget.db.close()
        lock.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--register', action='store_true')
    p.add_argument('--directory', type=Path, default=Path(os.getenv('DATABASE_PATH', 'data/riskgraph.sqlite3')).parent / VERSION)
    a = p.parse_args()
    if a.register:
        write(ROOT / 'docs/examples/travel-factorial-preregistration.json', registration())
        print('Matched protocol saved; no paid requests')
    else:
        run(a.directory)
