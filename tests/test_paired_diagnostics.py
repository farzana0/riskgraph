from copy import deepcopy
from math import factorial
import pytest
from scipy.stats import binomtest
from fastapi.testclient import TestClient
from app.main import create_app
from app.paired_demo import load_bundle, analyze, WEIGHTS, SCENARIOS
from app.paired_diagnostics import diagnostics, paired_interval, binomial_endpoints, PAIRED_ENDPOINT_ALPHA


def ids(bundle, split='heldout'):
    return [t['id'] for t in bundle[split]['traces']]


def test_endpoint_reference_and_discordance_edge_cases():
    for k,n in [(0,10),(4,10),(10,10),(3,60)]:
        ci=binomtest(k,n).proportion_ci(confidence_level=1-2*PAIRED_ENDPOINT_ALPHA,method='exact')
        assert binomial_endpoints(k,n,PAIRED_ENDPOINT_ALPHA)==pytest.approx([ci.low,ci.high])
    assert paired_interval(0,0,0)==[-1,1]
    assert paired_interval(60,0,60)[0]>0
    assert paired_interval(10,0,10)[0]<0  # Ten pairs remain inconclusive under the 72-endpoint budget.
    assert paired_interval(0,60,60)[1]<0
    with pytest.raises(ValueError):paired_interval(4,7,10)
    with pytest.raises(ValueError):paired_interval(-1,0,10)
    assert 6*3*4*PAIRED_ENDPOINT_ALPHA==pytest.approx(.05)


def test_paired_contrast_exhaustive_small_multinomial_coverage():
    # Directly enumerate all paired 2×2 tables, including dependent outcomes.
    n=5; alpha=.03
    for probabilities in [(0.1,.5,.1,.3),(.45,.05,.05,.45),(.25,.25,.25,.25),(0.,.9,.1,0.)]:
        truth=probabilities[1]-probabilities[2]
        coverage=0.
        for both in range(n+1):
            for avoided in range(n-both+1):
                for introduced in range(n-both-avoided+1):
                    neither=n-both-avoided-introduced
                    counts=[both,avoided,introduced,neither]
                    probability=factorial(n)
                    for count,p in zip(counts,probabilities):probability*=p**count/factorial(count)
                    low,high=paired_interval(avoided,introduced,n,alpha)
                    if low-1e-12<=truth<=high+1e-12:coverage+=probability
        assert coverage>=1-4*alpha-1e-12


def test_reference_differences_pairing_and_sensitivity_preserve_base_model():
    b=load_bundle(); admitted=ids(b); before=deepcopy(b)
    base=analyze(b,admitted)
    result=diagnostics(b,admitted,WEIGHTS)
    assert b==before
    assert result==diagnostics(b,admitted+admitted[:4],WEIGHTS)
    for cfg,row in result['paired_comparisons'].items():
        assert row['completed_pairs']==60
        assert row['observed_risk_reduction']==pytest.approx(base['projections']['none']['empirical']-base['projections'][cfg]['empirical'])
        assert row['mean_exposure_reduction_cents']==pytest.approx(base['projections']['none']['mean_exposure_cents']-base['projections'][cfg]['mean_exposure_cents'])
        assert row['introduced_cases']==0
        assert row['observed_legitimate_completion_change']==0
        assert row['confidence95'][0]<=row['observed_risk_reduction']<=row['confidence95'][1]
        for cell in row['cells'].values():
            assert cell['n']==cell['avoided']+cell['introduced']+cell['both_harmful']+cell['neither_harmful']
        selected=result['prior_sensitivity'][cfg][0]
        assert selected['posterior_mean']==base['projections'][cfg]['posterior_mean']
        assert selected['credible95']==base['projections'][cfg]['credible95']
    expected_variance=sum(w*w for w in WEIGHTS.values())*11/(12*12*13)
    assert result['posterior_moments']['rules']['variance']==pytest.approx(expected_variance)
    assert result['posterior_moments']['rules']['standard_deviation']**2==pytest.approx(expected_variance)
    means=[x['posterior_mean'] for x in result['prior_sensitivity']['rules']]
    assert sorted(means)==pytest.approx([.5/11,1/12,2/14])
    assert 'not a joint 95%' in result['error_budget_note']


def test_introduced_harm_and_missing_errors_are_not_hidden():
    b=deepcopy(load_bundle()); weights={s:float(s=='normal') for s in SCENARIOS}
    rec=next(r for r in b['heldout']['cases'] if r['family']=='normal')
    t=next(t for t in b['heldout']['traces'] if t['id']==rec['id']+':reviewer')
    # A binary-outcome test control: exercise a harmful intervention, not the refund generator.
    t['outcome']['unauthorized']=True;t['outcome']['exposure_cents']=1000
    result=diagnostics(b,ids(b),weights)
    row=result['paired_comparisons']['reviewer']
    assert row['introduced_cases']==1 and row['observed_risk_reduction']==pytest.approx(-.1)
    assert row['joint_posterior_reduction']['mean']<0
    assert row['mean_exposure_reduction_cents']==-100
    missing=diagnostics(b,ids(b)[:-1],weights)
    assert not missing['fixed_batch_eligible']
    assert all(r['confidence95'] is None for r in missing['paired_comparisons'].values())
    failed=diagnostics(b,ids(b,'walkthrough'),WEIGHTS,split='walkthrough')
    assert not failed['fixed_batch_eligible']
    assert all(r['completed_pairs']==2 for r in failed['paired_comparisons'].values())
    assert failed['paired_comparisons']['reviewer']['observed_legitimate_completion_change']==-1
    with pytest.raises(ValueError):diagnostics(b,['not-existing'],WEIGHTS)
    t['output_digest']='unmatched'
    with pytest.raises(ValueError,match='Paired outputs'):diagnostics(b,ids(b),WEIGHTS)


def test_diagnostics_api_real_archive_has_no_fixed_batch_guarantee():
    c=TestClient(create_app(':memory:',seed_demo=False)); b=load_bundle()
    body={'admitted_ids':ids(b,'recorded'),'weights':WEIGHTS,'split':'recorded'}
    r=c.post('/api/paired-demo/diagnostics',json=body)
    assert r.status_code==200
    assert not r.json()['fixed_batch_eligible']
    assert all(x['observed_risk_reduction'] is None for x in r.json()['paired_comparisons'].values())
    assert c.post('/api/paired-demo/diagnostics',json={**body,'weights':{}}).status_code==422


def test_joint_posterior_matches_beta_marginals_and_direct_dirichlet_reference():
    import numpy as np
    from app.paired_diagnostics import joint_paired_posterior
    b=load_bundle();base=analyze(b,ids(b),a=2,b=3);d=diagnostics(b,ids(b),WEIGHTS,a=2,b=3)
    for config,row in d['paired_comparisons'].items():
        expected=base['projections']['none']['posterior_mean']-base['projections'][config]['posterior_mean']
        assert row['joint_posterior_reduction']['mean']==pytest.approx(expected)
    cells={s:{'n':10,'avoided':3,'introduced':1,'both_harmful':2,'neither_harmful':4} for s in SCENARIOS}
    weights={s:float(s=='normal') for s in SCENARIOS}
    result=joint_paired_posterior(cells,weights,1.,2.)
    prior=np.array([1/3,2/3,2/3,4/3])
    assert prior[0]+prior[1]==pytest.approx(1.)
    assert prior[0]+prior[2]==pytest.approx(1.)
    alpha=prior+np.array([2,3,1,4])
    draws=np.random.default_rng(7).dirichlet(alpha,100000)
    contrast=draws[:,1]-draws[:,2]
    assert result['mean']==pytest.approx(2/13)
    assert contrast.mean()==pytest.approx(result['mean'],abs=.003)
    assert contrast.var()==pytest.approx(result['variance'],abs=.001)
    assert np.quantile(contrast,[.025,.975])==pytest.approx(result['credible95'],abs=.012)
