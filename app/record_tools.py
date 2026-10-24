"""Deterministic record calculations; no scoring oracle, model calls or payments."""
from datetime import datetime
from .hardcases import digest


def unique(rows,key):
    result={}
    for row in rows:
        name=row[key]
        if name in result and result[name]!=row:raise ValueError('Conflicting duplicate identifier')
        result[name]=row
    return result


def calculate(observation):
    records=observation['authenticated_connector_records'];request=observation['authenticated_request']
    facts={};sources={};errors=[];order=request['order_id']
    def put(name,value,ref):
        if name in facts and facts[name]!=value:raise ValueError('Conflicting current facts: '+name)
        facts[name]=value;sources[name]=ref
    try:
        for i,r in enumerate(records):
            ref='authenticated_connector_records['+str(i)+']'
            if r.get('order_id',order)!=order:continue
            if 'owner_account_id' in r:put('owner_account_id',r['owner_account_id'],ref+'.owner_account_id')
            if 'age_days' in r:put('age_days',r['age_days'],ref+'.age_days')
            if 'paid_at' in r:
                start,end=datetime.fromisoformat(r['paid_at']),datetime.fromisoformat(r['evaluated_at'])
                if start.utcoffset() is None or end.utcoffset() is None:raise ValueError('Explicit time-zone offsets required')
                seconds=int((end-start).total_seconds())
                if seconds<0:raise ValueError('Payment timestamp is in the future')
                put('elapsed_seconds',seconds,ref+'.paid_at,evaluated_at');put('age_days',seconds//86400,ref+'.paid_at,evaluated_at')
            if r.get('connector')=='identity':
                if r.get('authenticated_subject')!=request.get('authenticated_subject'):raise ValueError('Identity subject does not match request')
                rows=r['bindings'];latest=max(x['sequence'] for x in rows)
                ids={x['account_id'] for x in rows if x['sequence']==latest}
                if len(ids)!=1:raise ValueError('Conflicting highest-sequence identity')
                put('authenticated_account_id',ids.pop(),ref+'.bindings');put('identity_sequence',latest,ref+'.bindings')
            if 'snapshots' in r:
                rows=[x for x in r['snapshots'] if x.get('order_id',order)==order]
                latest=max(x['sequence'] for x in rows);current=[x for x in rows if x['sequence']==latest]
                states={(x['paid_cents'],x['refunded_cents']) for x in current}
                if len(states)!=1:raise ValueError('Conflicting highest-sequence snapshot')
                paid,spent=states.pop();put('remaining_usd_cents',max(0,paid-spent),ref+'.snapshots');put('ledger_sequence',latest,ref+'.snapshots')
            elif r.get('connector')=='fx_reservations':
                rows=unique(r['reservations'],'id').values()
                spent=sum(r['posted_refunds_source_minor'])+sum(x['minor'] for x in rows if x['order_id']==order and x['status']=='active')
                rate=r['usd_cents_per_source_minor'];num,den=rate['numerator'],rate['denominator']
                if not isinstance(num,int) or not isinstance(den,int) or num<=0 or den<=0:raise ValueError('Positive rational FX rate required')
                remaining=max(0,r['paid_source_minor']-spent)
                put('remaining_source_minor',remaining,ref);put('remaining_usd_cents',remaining*num//den,ref)
            elif 'events' in r:
                rows=unique(r['events'],'id')
                if any(x.get('kind')=='reversal' for x in rows.values()):
                    children={}
                    for x in rows.values():
                        if x.get('kind')=='reversal':
                            parent=x['reverses']
                            if parent not in rows or parent in children:raise ValueError('Dangling or branching reversal reference')
                            children[parent]=x['id']
                    def active(key,seen):
                        if key in seen:raise ValueError('Cyclic reversal references')
                        return key not in children or not active(children[key],seen|{key})
                    # Validate every component, including cycles disconnected from roots.
                    for key in rows:active(key,set())
                    spent=sum(x['cents'] for x in rows.values() if x.get('kind')=='refund' and active(x['id'],set()))
                else:spent=sum(x['cents'] for x in rows.values() if x.get('status')=='posted')
                put('consumed_usd_cents',spent,ref+'.events');put('remaining_usd_cents',max(0,r['paid_cents']-spent),ref)
            elif 'paid_cents' in r and 'refunded_cents' in r:
                put('remaining_usd_cents',max(0,r['paid_cents']-r['refunded_cents']),ref)
        if 'subject_account_id' in request:put('authenticated_account_id',request['subject_account_id'],'authenticated_request.subject_account_id')
        for key in ('owner_account_id','authenticated_account_id','age_days','remaining_usd_cents'):
            if key not in facts:errors.append('Missing '+key)
    except (ValueError,KeyError,TypeError,RecursionError) as exc:
        errors.append(str(exc));facts={};sources={}
    return {'version':'record-calculations-v1','input_sha256':digest(observation),'status':'complete' if not errors else 'unresolved',
        'facts':facts,'source_paths':sources,'issues':errors,'authority':'Current-record calculations only; not a refund authorization.'}
