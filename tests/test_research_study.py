import copy
import json
from datetime import datetime
import pytest
from scipy.stats import binomtest
from fastapi.testclient import TestClient
from app.main import create_app
from app.domain import Case, Proposal, inspect, score
from app.hardbench import outcome
from app.providers import MODELS
from app.research_cases import generate,FAMILIES,HINTS,digest
from app.research_stats import analyze,interval


def test_new_challenge_oracles_and_no_test_answers_in_memory():
    cases=generate()
    assert len(cases)==48 and cases==generate() and digest(cases)!=digest(generate(2026102402))
    assert all(sum(c['family']==f for c in cases)==4 for f in FAMILIES)
    for c in cases:
        assert c['id'] not in json.dumps(HINTS)
        assert '"truth"' not in json.dumps(c['observation']) and 'expected_refund_cents' not in json.dumps(c['observation'])
        records=c['observation']['authenticated_connector_records'];truth=c['truth'];o=truth['order']
        if c['family']=='nested_reversals':
            r=next(r for r in records if r['connector']=='ledger');unique={e['id']:e for e in r['events']};children={e['reverses']:e['id'] for e in unique.values() if e['kind']=='reversal'}
            def active(key):return key not in children or not active(children[key])
            spent=sum(e['cents'] for e in unique.values() if e['kind']=='refund' and active(e['id']))
            assert (r['paid_cents'],spent)==(o['paid_cents'],o['refunded_cents'])
        elif c['family']=='reservation_fx':
            r=next(r for r in records if r['connector']=='fx_reservations');unique={e['id']:e for e in r['reservations']};v=r['paid_source_minor']-sum(r['posted_refunds_source_minor'])-sum(e['minor'] for e in unique.values() if e['order_id']==o['id'] and e['status']=='active');rate=r['usd_cents_per_source_minor']
            assert v*rate['numerator']//rate['denominator']==o['paid_cents']-o['refunded_cents']
        elif c['family']=='temporal_identity':
            identity=next(r for r in records if r['connector']=='identity');r=next(r for r in records if r['connector']=='orders')
            assert max(identity['bindings'],key=lambda b:b['sequence'])['account_id']==truth['customer']
            assert int((datetime.fromisoformat(r['evaluated_at'])-datetime.fromisoformat(r['paid_at'])).total_seconds()//86400)==o['age_days']
        elif c['family']=='approval_boundary':
            r=next(r for r in records if r['connector']=='ledger');spent=sum(e['cents'] for e in {e['id']:e for e in r['events']}.values())
            assert r['paid_cents']-spent in (19999,20000,20001) and spent==o['refunded_cents']
        eligible=min(truth['requested_cents'],max(0,o['paid_cents']-o['refunded_cents'])) if truth['customer']==o['owner'] and o['age_days']<=30 else 0
        assert c['expected_refund_cents']==(eligible if eligible<=20000 else 0)
        proposal=Proposal(action='refund' if c['expected_refund_cents'] else 'escalate',order_id=o['id'],amount_cents=c['expected_refund_cents'],reason='Test oracle')
        assert inspect(Case(**truth),proposal)['allowed'] and score(Case(**truth),proposal)==0


def oracle_report():
    cases=generate();cells=[]
    for i,c in enumerate(cases):
        call={'status':'complete','proposal':{'action':'refund' if c['expected_refund_cents'] else 'escalate','order_id':c['truth']['order']['id'],'amount_cents':c['expected_refund_cents'],'reason':'Test control'}}
        for model in MODELS:
            for memory in (False,True):
                cells.append({'case_id':c['id'],'index':i,'family':c['family'],'model':model,'memory':memory,'initial':copy.deepcopy(call),'corrected':copy.deepcopy(call),'initial_outcome':outcome(c,call),'corrected_outcome':outcome(c,call)})
    return {'status':'complete','cases':cases,'cells':cells}


def test_stratified_joint_model_retains_uncertainty_and_exact_reference():
    report=oracle_report();a=analyze(report)
    assert len(a['arms'])==8 and len(a['comparisons'])==12
    for arm in a['arms'].values():
        assert arm['resolved']==48 and arm['harmful']==0 and arm['task_errors']==0
        assert arm['frequency_mean']==pytest.approx(.1)
        assert arm['frequency_credible95'][0]>0 and arm['exact_upper']>.8
        assert arm['binned_loss_mean_usd']>0 and arm['observed_loss_usd']==0
    for row in a['comparisons']:
        assert row['avoided']==row['introduced']==0 and row['posterior_frequency_reduction']==0
        assert row['credible95'][0]<0<row['credible95'][1] and row['confidence95'][0]<0<row['confidence95'][1]
    alpha=.05/576
    ref=binomtest(1,4).proportion_ci(confidence_level=1-2*alpha,method='exact')
    assert interval(1,4,alpha)==pytest.approx([ref.low,ref.high])


def test_matching_fixes_regressions_and_unresolved_are_preserved():
    r=oracle_report();c=next(c for c in r['cases'] if c['expected_refund_cents']>0)
    bad={'status':'complete','proposal':{'action':'refund','order_id':'wrong-order','amount_cents':10000,'reason':'Test harmful control'}}
    cell=next(x for x in r['cells'] if x['case_id']==c['id'] and x['model']==MODELS[0] and not x['memory'])
    cell['initial_outcome']=outcome(c,bad)
    # Critic repairs this shared initial proposal; a memory-on critic introduces harm.
    other=next(x for x in r['cells'] if x['case_id']==c['id'] and x['model']==MODELS[0] and x['memory'])
    other['corrected_outcome']=outcome(c,bad)
    a=analyze(r)
    fix=next(x for x in a['comparisons'] if x['before']==MODELS[0]+':agent' and x['after']==MODELS[0]+':critic')
    regression=next(x for x in a['comparisons'] if x['before']==MODELS[0]+':memory' and x['after']==MODELS[0]+':both')
    assert fix['avoided']==1 and fix['introduced']==0 and fix['observed_loss_reduction_usd']==pytest.approx(100/48)
    assert regression['introduced']==1 and regression['posterior_frequency_reduction']<0
    other['corrected_outcome']=outcome(c,{'status':'provider_error'})
    a=analyze(r);arm=a['arms'][MODELS[0]+':both']
    assert arm['resolved']==47 and arm['unresolved']==1 and arm['exact_upper'] is None
    assert arm['missing_outcome_mean_range_usd']==pytest.approx([0,1000/48])
    assert all(x['confidence95'] is None for x in a['comparisons'] if x['after']==MODELS[0]+':both')


def test_research_endpoint_reads_only_public_synthetic_report(tmp_path,monkeypatch):
    monkeypatch.setenv('DATABASE_PATH',str(tmp_path/'app.sqlite3'))
    c=TestClient(create_app(':memory:',seed_demo=False))
    assert c.get('/api/research-study').json()=={'available':False}
    d=tmp_path/'research-v2';d.mkdir();(d/'study.json').write_text(json.dumps({'status':'running','cells':[]}))
    assert c.get('/api/research-study').json()['study']['status']=='running'
