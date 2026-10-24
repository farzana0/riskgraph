"""Fixed fresh-case legacy/grounded factorial comparison, under one capped ledger."""
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
from app.travel_v3 import VERSION, SEED, WORKFLOWS, BANK, TAG, generate, entry, fact_text, select_memory, context, payload, outcome, record_view
from app.travel_v3_stats import analyze
from app.travel_factorial import call
from app.hardcases import digest
from app.live_budget import LiveBudget
from app.providers import MODELS, Agent, AgentMemory
from scripts.hard_benchmark import write

ROOT = Path(__file__).resolve().parents[1]
MAX_USD = 7.5
SOURCES = ['app/travel_v3.py', 'app/travel_v3_stats.py', 'scripts/travel_v3.py', 'app/travel_factorial.py',
           'app/travel_factorial_stats.py', 'app/travel.py', 'app/live_budget.py', 'app/travel_calls.py', 'app/providers.py', 'app/hardbench.py']


def registration():
    return {'version': VERSION, 'seed': SEED, 'cases': 32, 'cases_sha256': digest(generate()),
            'workflows': list(WORKFLOWS), 'models': list(MODELS), 'critic_model': MODELS[1],
            'max_usd': MAX_USD, 'max_requests': 512,
            'bank_sha256': digest({s: entry(s) for s in BANK}),
            'legacy_archive_sha256': hashlib.sha256((ROOT / 'docs/examples/travel-factorial.json').read_bytes()).hexdigest(),
            'settings': {'max_tokens': 1536, 'thinking': 'adaptive', 'effort': 'low', 'output_schema': 'identical unchanged Booking JSON schema for every arm'},
            'source_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES},
            'scope': '32 fresh harder trips, four per eight equal-weight families. Both frozen legacy and revised record-grounded workflows cross two models, memory off/on, and the same Sonnet critic off/on. 16 configurations, 512 planned calls. Critic-off reuses initial proposals. Fresh exact-second boundaries, UTC offsets, 40-60 fee items, competing revisions, ledger distractors and multiple valid alternatives. Eight no-eligible controls. All API/model/schema/thinking/effort/token settings remain unchanged. Grounded workflow adds source-bound arithmetic for every arm, compact procedural memory when enabled, and a concrete-evidence critic that omits the initial prose. Across-workflow effects test that package, not memory alone. Discovery and old observations are excluded. No retries, outcome-driven case additions or extension. US$7.50 held-out cap plus a separate US$0.50 discovery cap: at most US$8 new spending.'}


def freeze(directory):
    path = directory / 'memory.json'
    if path.exists():
        saved = json.loads(path.read_text())
        assert saved['bank_sha256'] == registration()['bank_sha256']
        return saved
    old = json.loads((ROOT / 'docs/examples/travel-factorial.json').read_text())['memory']
    memory = AgentMemory()
    if not memory.configured: raise RuntimeError('Actual hosted memory required')
    current = {'selected': {}, 'retrievals': {}, 'write_turn_ids': {}}
    for skill in BANK:
        stored = memory._post('/facts', {'text': fact_text(skill), 'infer': 'full', 'scopes': [[memory.scope]]}, TAG + '-' + skill)
        response = memory._post('/query', {'query': TAG + ' ' + skill + ' ' + digest(entry(skill)), 'k': 8,
                                          'lens': [[memory.scope]], 'scopeView': 'strict', 'mode': 'hybrid'})
        clean = {'hits': [{'id': h.get('id'), 'text': str(h.get('text', ''))} for h in response.get('hits', []) if TAG in str(h.get('text', ''))],
                 'trace': {'traceId': response.get('trace', {}).get('traceId')}}
        current['selected'][skill] = select_memory(skill, clean); current['retrievals'][skill] = clean
        current['write_turn_ids'][skill] = stored.get('turnId')
    saved = {'legacy': old, 'grounded': current, 'bank_sha256': registration()['bank_sha256']}
    write(path, saved); return saved


def execute(directory, case, model, mode, workflow, memory):
    budget = LiveBudget(directory / 'requests.sqlite3', MAX_USD, 512)
    client = httpx.Client(timeout=90)
    try:
        agent = Agent(client); memories = context(memory, mode == 'selected', workflow)
        prefix = VERSION + ':' + case['id'] + ':' + model + ':' + mode + ':' + workflow
        try: initial = call(agent, budget, payload(case['observation'], memories, model, workflow=workflow), prefix + ':initial')
        except RuntimeError: initial = {'status': 'not_started', 'code': 'budget_or_unknown'}
        try:
            corrected = call(agent, budget, payload(case['observation'], memories, MODELS[1], initial['proposal'], workflow), prefix + ':critic') if initial['status'] == 'complete' else {'status': 'not_started', 'code': 'initial_proposal_unavailable'}
        except RuntimeError: corrected = {'status': 'not_started', 'code': 'budget_or_unknown'}
        return {'case_id': case['id'], 'family': case['family'], 'workflow': workflow, 'model': model, 'memory_mode': mode,
                'context_sha256': digest(memories), 'record_view_sha256': digest(record_view(case['observation'])) if workflow == 'grounded' else None,
                'initial': initial, 'initial_outcome': outcome(case, initial), 'corrected': corrected, 'corrected_outcome': outcome(case, corrected)}
    finally: client.close(); budget.db.close()


def run(directory, discovery=False):
    directory.mkdir(parents=True, exist_ok=True)
    lock = (directory / 'study.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    design = registration(); assert design == json.loads((ROOT / 'docs/examples/travel-v3-preregistration.json').read_text())
    if discovery:
        from scripts.travel_discovery import run as discover
        discover(directory.parent / 'travel-discovery-v1')
    memory = freeze(directory); design = {**design, 'retrieved_memory_sha256': digest(memory)}
    budget = LiveBudget(directory / 'requests.sqlite3', MAX_USD, 512); budget.pin(design)
    cases = generate(); s = {'schema_version': VERSION, 'design': design, 'cases': cases, 'memory': memory,
                            'cells': [], 'status': 'running', 'budget': budget.totals()}
    path = directory / 'study.json'; write(path, s)
    try:
        with ThreadPoolExecutor(8) as pool:
            for index, c in enumerate(cases):
                arms = [(m, mode, w) for w in WORKFLOWS for m in MODELS for mode in ('none', 'selected')]
                random.Random(20261024179 + index).shuffle(arms)
                s['cells'].extend(pool.map(lambda arm: execute(directory, c, *arm, memory), arms))
                s['budget'] = budget.totals(); write(path, s)
                print(json.dumps({'case': index + 1, 'scheduled': 32, 'budget': s['budget']}), flush=True)
                calls = [r[t] for r in s['cells'] for t in ('initial', 'corrected')]
                if any(r['status'] == 'provider_error' for r in calls): s['status'] = 'provider_error'; break
                if any(r.get('code') == 'budget_or_unknown' for r in calls): s['status'] = 'budget_limited'; break
            else: s['status'] = 'complete'
        s['processed_cases'] = len({r['case_id'] for r in s['cells']}); s.update(analyze(s)); s['budget'] = budget.totals(); write(path, s)
    finally: budget.db.close(); lock.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--register', action='store_true'); p.add_argument('--with-discovery', action='store_true')
    p.add_argument('--directory', type=Path, default=Path(os.getenv('DATABASE_PATH', 'data/riskgraph.sqlite3')).parent / VERSION)
    a = p.parse_args()
    if a.register: write(ROOT / 'docs/examples/travel-v3-preregistration.json', registration())
    else: run(a.directory, a.with_discovery)
