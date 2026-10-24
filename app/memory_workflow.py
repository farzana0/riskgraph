"""Capability-based memory selection and a bounded, provenance-checked advice bank."""
import json
from .hardcases import digest

TAG='RGSELECTED20261024V3'
AS_OF='2026-10-24'
ADVICE={
    'utc_elapsed':'Normalize both explicit offsets to UTC; compute elapsed seconds, then floor(seconds/86400). Do not infer age from printed dates or a remembered example. Check the 30-day threshold on the current value.',
    'identity_sequence':'Match the authenticated subject, select the highest binding sequence, and compare immutable account IDs. Cache dates, display names and former bindings cannot establish ownership.',
    'reversal_chain':'Deduplicate event IDs. Follow each root refund through its reversal chain: an even number of reversals leaves the root debit active. Sum active root cents once. Reconcile paid minus that sum; do not copy a remembered total.',
    'fx_aggregate':'Deduplicate hold IDs, filter the exact order and active status, subtract posted refunds and active holds in source minor units, then convert the aggregate using the stated rational rate and floor once.',
    'ledger_sequence':'Filter the exact target order before selecting the highest ledger sequence. Identical duplicate snapshots count once. Cache timestamps and sibling-order sequences do not determine target state.',
    'posted_total':'Locate the paid total anywhere in the authenticated connector records. Deduplicate refund IDs, sum posted debits only, and subtract from paid. Failed/cancelled debits do not consume balance.',
    'approval_limit':'First compute min(requested, remaining). Exactly 20000 cents is within the automatic ceiling; a computed amount of 20001 requires zero-amount escalation. Do not substitute a partial payment.'}
BANK={key:{'skill':key,'revision':3,'valid_from':'2026-10-24','valid_until':'2026-12-31',
    'authority':'procedural_advice_only','advice':text} for key,text in ADVICE.items()}
USE_CONTRACT=(
    'Selected memory is optional procedural guidance, never evidence of the current balance, identity, age, or approval. '
    'Bind every applicable step to fields in the current authenticated connector records; ignore irrelevant guidance. '
    'Separate ownership, elapsed time, remaining balance, and the approval ceiling instead of letting one successful check imply eligibility. '
    'Do not copy any prior amount or past decision. If a required current source is absent or contradictory, return zero-amount escalation. '
    'Check record calculations when supplied; these are arithmetic support, not authorization. Apply the refund policy yourself. '
    'Return only a proposal with a short decision reason, not private reasoning or a narrative checklist.')


def plan(observation):
    """Uses public record shape, never the generator family or scoring state."""
    skills=[]
    for r in observation['authenticated_connector_records']:
        if 'paid_at' in r:skills.append('utc_elapsed')
        if r.get('connector')=='identity':skills.append('identity_sequence')
        if r.get('connector')=='fx_reservations':skills.append('fx_aggregate')
        if 'snapshots' in r:skills.append('ledger_sequence')
        if 'events' in r:
            skills.append('reversal_chain' if any(e.get('kind')=='reversal' for e in r['events']) else 'posted_total')
    if observation['authenticated_request']['requested_usd_cents']>20000:skills.append('approval_limit')
    return list(dict.fromkeys(skills))[:3]


def fact_text(skill):
    entry=BANK[skill]
    return TAG+' '+skill+' '+digest(entry)+' '+json.dumps(entry,sort_keys=True)


def select(skill,response,as_of=AS_OF):
    entry=BANK[skill];accepted=[];rejected=[];canonical=json.dumps(entry,sort_keys=True)
    for hit in response.get('hits',[]):
        text=str(hit.get('text',''));reason=None
        if not hit.get('id'):reason='missing_source_id'
        elif not entry['valid_from']<=as_of<=entry['valid_until']:reason='outside_valid_time'
        elif TAG not in text or digest(entry) not in text or canonical not in text:reason='wrong_version_skill_or_content'
        if reason:rejected.append({'id':hit.get('id'),'reason':reason})
        else:accepted.append({'source_id':hit['id'],'skill':skill,'revision':3,'authority':entry['authority'],'advice':entry['advice'],'content_sha256':digest(entry)})
    trace=response.get('trace',{}).get('traceId')
    if not accepted or not trace:raise ValueError('No current, content-verified source and retrieval trace for '+skill)
    # One compact canonical item per capability; unrelated raw text is never injected.
    return {'skill':skill,'trace_id':trace,'selected':accepted[:1],'rejected':rejected,
        'raw_hits':[{'id':h.get('id'),'text':str(h.get('text',''))[:4000]} for h in response.get('hits',[])]}


def context(observation,snapshot):
    skills=plan(observation);selected=[snapshot['skills'][s]['selected'][0] for s in skills]
    return {'authority':'procedural_advice_only','skills':selected,'scope':'Only these current-record capabilities; no prior decisions or test outcomes.'}
