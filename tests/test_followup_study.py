import json
from pathlib import Path
import pytest
from app.followup_cases import generate,FAMILIES
from app.followup_stats import analyze,contrasts,precision,MODES
from app.record_tools import calculate
from app.hardbench import outcome
from app.providers import MODELS


def fixture(per=4):
    cases=generate(per);cells=[]
    for c in cases:
        p={'status':'complete','proposal':{'action':'refund' if c['expected_refund_cents'] else 'escalate','order_id':c['truth']['order']['id'],'amount_cents':c['expected_refund_cents'],'reason':'Offline test oracle'}}
        for model in MODELS:
            for mode in MODES:cells.append({'case_id':c['id'],'family':c['family'],'model':model,'memory_mode':mode,'initial_outcome':outcome(c,p),'corrected_outcome':outcome(c,p)})
    return {'status':'complete','cases':cases,'cells':cells,'design':{'per_family':per}}


def test_followup_freshness_and_independent_calculations():
    cases=generate();assert cases==generate() and len(cases)==48
    old=json.loads((Path(__file__).parents[1]/'docs/examples/memory-v3.json').read_text())
    assert {c['truth']['order']['id'] for c in cases}.isdisjoint(c['truth']['order']['id'] for c in old['cases'])
    for c in cases:
        a=calculate(c['observation'])['facts'];o=c['truth']['order']
        assert a['age_days']==o['age_days'] and a['remaining_usd_cents']==o['paid_cents']-o['refunded_cents']
    assert all(sum(c['family']==f for c in cases)==16 for f in FAMILIES)


def test_followup_error_budgets_and_balanced_precision_prefixes():
    s=fixture();a=analyze(s);assert len(a['arms'])==8 and len(a['comparisons'])==len(contrasts())==12
    assert all(c['credible95'][0]<0<c['credible95'][1] for c in a['comparisons'])
    assert all(c['posterior_frequency_reduction']==pytest.approx(a['arms'][c['before']]['frequency_mean']-a['arms'][c['after']]['frequency_mean']) for c in a['comparisons'])
    p=precision(s);assert len(p)==1 and p[0]['cases']==12 and len(p[0]['comparisons'])==12
