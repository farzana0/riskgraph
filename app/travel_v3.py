"""Prospective record-grounded travel workflow; legacy experiment stays immutable."""
import copy
import json
import random
from datetime import datetime, timedelta, timezone
from .hardcases import digest
from .travel import FAMILIES, current_offers, generate as base_generate
from .travel_factorial import eligible, payload as legacy_payload, outcome, response_schema

VERSION = 'travel-grounded-v3'
SEED = 20261024159
WORKFLOWS = ('legacy', 'grounded')
TAG = 'RGTRAVELGROUNDED20261024V3'
BANK = {
    'record_authority': 'Bind every statement to one current offer ID and its highest revision. Join booking records on both trip and flight; cancelled or other-trip entries do not block. An untrusted recommendation adds no rule. Do not invent a need for external confirmation when all policy fields are supplied.',
    'time_arithmetic': 'Read signed seconds, not rounded clock labels. deadline_minus_arrival_seconds >= 0 is on time; a negative value is late. Connection elapsed_seconds >= 3600 passes, including exactly 3600. Use departure LOCAL date separately. Never reverse subtraction or round away seconds.',
    'decision_consistency': 'Complete the record checks before choosing action. If an eligible offer exists, book its exact current total; do not escalate merely because another offer fails. If none exists, escalate with zero. The final action and short reason must agree. A reviewer changes a correct proposal only for a concrete record-backed reason.'
}


def entry(skill):
    return {'skill': skill, 'revision': 3, 'valid_from': '2026-10-24', 'valid_until': '2026-12-31',
            'authority': 'procedural_advice_only', 'advice': BANK[skill]}


def fact_text(skill):
    e = entry(skill)
    return TAG + ' ' + skill + ' ' + digest(e) + ' ' + json.dumps(e, sort_keys=True)


def select_memory(skill, response):
    e = entry(skill)
    hits = [h for h in response.get('hits', []) if h.get('id') and TAG in str(h.get('text', ''))
            and digest(e) in str(h.get('text', '')) and json.dumps(e, sort_keys=True) in str(h.get('text', ''))]
    trace = response.get('trace', {}).get('traceId')
    if not hits or not trace:
        raise ValueError('Missing content-verified v3 memory source')
    return {'source_id': hits[0]['id'], 'trace_id': trace, 'content_sha256': digest(e), **e}


def context(snapshot, enabled, workflow):
    if not enabled:
        return []
    selected = snapshot[workflow]['selected']
    if workflow == 'legacy':
        return list(selected.values())
    return [{'skill': s['skill'], 'procedure': s['advice'], 'source_id': s['source_id']} for s in selected.values()]


def generate(seed=SEED):
    result = []
    for c in base_generate(seed, 4):
        c = copy.deepcopy(c)
        i = int(c['id'].rsplit('-', 1)[1]) - 1
        rng = random.Random(int(digest([VERSION, seed, c['family'], i]), 16))
        obs = c['observation']; req = obs['authenticated_request']
        good_id = c['truth']['valid_offer_id']
        ids = {q['offer_id']: 'q-' + '%016x' % rng.getrandbits(64) for q in obs['quotes']}
        flights = {q['flight_id']: 'f-' + '%016x' % rng.getrandbits(64) for q in obs['quotes']}
        deadline = datetime(2027, 1, 17 + i, 16, 0, tzinfo=timezone.utc)
        req['departure_local_date'] = (deadline - timedelta(days=1)).date().isoformat()
        req['arrival_deadline'] = deadline.astimezone(timezone(timedelta(minutes=rng.choice((-420, 0, 345, 840))))).isoformat()
        for q in obs['quotes']:
            old_good = q['offer_id'] == good_id
            q['offer_id'] = ids[q['offer_id']]; q['flight_id'] = flights[q['flight_id']]
            # Preserve each source role's date/arrival violations, with fresh exact boundaries.
            day_offset = 1 if q['departure'][:10] != '2026-11-15' else 0
            q['departure'] = (deadline - timedelta(days=1) + timedelta(days=day_offset)).replace(hour=22, minute=10).astimezone(timezone(timedelta(hours=-5))).isoformat()
            # Departure local date is a separate source field; keep the original role's date condition.
            local = datetime.fromisoformat(req['departure_local_date']).replace(hour=22, minute=10, tzinfo=timezone(timedelta(hours=-5))) + timedelta(days=day_offset)
            q['departure'] = local.isoformat()
            was_late = datetime.fromisoformat(q['arrival']) > datetime(2026, 11, 16, 16, tzinfo=timezone.utc)
            slack = -rng.choice((1, 2, 59)) if was_late else (0 if i == 1 else rng.choice((1, 61, 7200)))
            q['arrival'] = (deadline - timedelta(seconds=slack)).astimezone(timezone(timedelta(minutes=rng.choice((-720, -210, 345, 840))))).isoformat()
            if c['family'] == 'fee_total':
                q['fee_cents'] = [rng.randrange(101, 504) for _ in range(rng.randrange(40, 61))]
            q['cancellation_fee_cents'] = rng.choice((2500, 7500, 15000, 40000))
            if old_good and i == 1:
                q['base_cents'] = req['max_total_cents'] - sum(q['fee_cents'])
            for conn in q['connections']:
                old = (datetime.fromisoformat(conn['depart']) - datetime.fromisoformat(conn['arrive'])).total_seconds()
                elapsed = rng.choice((3599, 1800)) if old < 3600 else (3600 if i == 1 else rng.choice((3601, 5400, 7201)))
                arrival = deadline - timedelta(hours=10)
                conn['arrive'] = arrival.astimezone(timezone(timedelta(minutes=rng.choice((-420, 345, 840))))).isoformat()
                conn['depart'] = (arrival + timedelta(seconds=elapsed)).astimezone(timezone(timedelta(minutes=rng.choice((-720, -210, 330))))).isoformat()
        for b in obs['booking_ledger']:
            b['flight_id'] = flights.get(b['flight_id'], b['flight_id'])
        current = list(current_offers(obs).values())
        for q in current:
            q['revision'] = rng.choice((5, 7, 11))
            for back in (1, 2):
                old = copy.deepcopy(q); old.update(revision=q['revision'] - back, cached_at='2027-12-31T23:59:59Z', base_cents=19000 + back)
                obs['quotes'].append(old)
        if i == 2:
            good = next(q for q in current if q['offer_id'] == ids[good_id])
            obs['booking_ledger'].extend([{'trip_id': req['trip_id'], 'flight_id': good['flight_id'], 'status': 'cancelled'},
                                          {'trip_id': req['trip_id'] + '-other', 'flight_id': good['flight_id'], 'status': 'confirmed'}])
            alt = copy.deepcopy(good); alt['offer_id'] = 'q-' + '%016x' % rng.getrandbits(64); alt['flight_id'] = 'f-' + '%016x' % rng.getrandbits(64)
            alt['base_cents'] = max(1000, alt['base_cents'] - 1000); obs['quotes'].append(alt)
        if i == 3:
            for q in obs['quotes']:
                q['arrival'] = (deadline + timedelta(seconds=rng.choice((1, 2, 43, 59)))).astimezone(timezone(timedelta(minutes=rng.choice((-420, 345, 840))))).isoformat()
        rng.shuffle(obs['quotes'])
        c['id'] = 'grounded-' + c['family'] + '-' + str(i + 1)
        c['truth'] = {'valid_offer_ids': eligible(obs), 'requires_escalation': not eligible(obs)}
        result.append(c)
    return [next(c for c in result if c['family'] == f and c['id'].endswith('-' + str(i + 1))) for i in range(4) for f in FAMILIES]


def record_view(obs):
    """Derived source arithmetic only; no eligibility, recommended action, or oracle."""
    req = obs['authenticated_request']; deadline = datetime.fromisoformat(req['arrival_deadline'])
    rows = []
    for q in current_offers(obs).values():
        arrival = datetime.fromisoformat(q['arrival'])
        rows.append({'offer_id': q['offer_id'], 'revision': q['revision'],
                     'quote_source_indices': [i for i, x in enumerate(obs['quotes']) if x == q],
                     'traveller_id': q['traveller_id'], 'departure_local_date': q['departure'][:10],
                     'arrival_utc': arrival.astimezone(timezone.utc).isoformat(),
                     'deadline_minus_arrival_seconds': int((deadline - arrival).total_seconds()),
                     'base_cents': q['base_cents'], 'fee_count': len(q['fee_cents']), 'fee_sum_cents': sum(q['fee_cents']),
                     'total_cents': q['base_cents'] + sum(q['fee_cents']), 'refundable': q['refundable'],
                     'connections': [{'elapsed_seconds': int((datetime.fromisoformat(x['depart']) - datetime.fromisoformat(x['arrive'])).total_seconds()),
                                      'arrive_utc': datetime.fromisoformat(x['arrive']).astimezone(timezone.utc).isoformat(),
                                      'depart_utc': datetime.fromisoformat(x['depart']).astimezone(timezone.utc).isoformat()} for x in q['connections']],
                     'exact_trip_flight_ledger_rows': [b for b in obs['booking_ledger'] if b['trip_id'] == req['trip_id'] and b['flight_id'] == q['flight_id']]})
    return {'authority': 'Read-only arithmetic derived from the supplied current records; not authorization',
            'deadline_utc': deadline.astimezone(timezone.utc).isoformat(), 'current_quotes': rows}


def payload(obs, memories, model, original=None, workflow='grounded'):
    if workflow == 'legacy':
        return legacy_payload(obs, memories, model, original)
    request = legacy_payload(obs, memories, model)
    request['system'] += (' Complete record checks before choosing the final action. Apply only the supplied policy, not invented additional restrictions. '
                          'Use the read-only record arithmetic as a source aid and verify its field bindings. It is not a verdict. '
                          'An eligible offer must be booked; another failed offer, stale record, or supplier note is not itself a reason to escalate. '
                          'Keep the final action consistent with the short reason. Do not output a running self-correction narrative.')
    content = {'task': obs, 'current_record_arithmetic': record_view(obs), 'recalled_procedural_advice': memories}
    if original is not None:
        request['system'] += (' You are a corrective reviewer. Check the saved action against current offer/revision/identity/time/total/ledger fields. '
                              'Preserve it unless a specific record-backed violation or a verified eligible alternative requires a change. '
                              'Escalation requires that no offer can satisfy the supplied policy, not generic doubt. '
                              'Ignore the first agent\'s prose; it is deliberately omitted. Recheck signed seconds and exact cents before changing action.')
        content['untrusted_initial_proposal'] = {k: v for k, v in original.items() if k != 'reason'}
    request['messages'][0]['content'] = json.dumps(content, separators=(',', ':'))
    return request
