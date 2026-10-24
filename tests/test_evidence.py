import copy
import json
import pytest
from app.evidence import EvidenceBatch, ProjectionRequest, summarize, project
from app.travel import FAMILIES
from app.travel_factorial_stats import key
from app.providers import MODELS
from tests.test_travel_factorial import fixture


def batch(source='observed'):
    return {'source': source, 'system_version': 'system-reviewed-v1', 'reference_configuration': key(MODELS[0], 'none', False),
            'loss_cap_cents': 100000, 'episodes': [
                {'episode_id': 'episode-1', 'scenario': 'wrong_date', 'reviewed': True, 'review_ref': 'review-1', 'potential_loss_cents': 2500, 'executed_loss_cents': 0,
                 'events': [{'event_id': 'a', 'actor': 'agent', 'action': 'Propose'}, {'event_id': 'b', 'parent_ids': ['a'], 'actor': 'critic', 'action': 'Review'}]},
                {'episode_id': 'episode-2', 'scenario': 'wrong_date', 'reviewed': False, 'potential_loss_cents': None, 'executed_loss_cents': 0}]}


def study():
    s = fixture()
    for r in s['cells']: r['workflow'] = 'grounded'
    s['analysis'] = {'arms': {key(MODELS[0], 'none', False): {}}}
    return s


def test_episode_units_review_provenance_and_missing_loss():
    b = EvidenceBatch.model_validate(batch()).model_dump(); summary = summarize(b)
    assert summary['episodes'] == 2 and summary['reviewed_known_potential_loss'] == 1 and summary['unresolved_potential_loss'] == 1
    bad = batch(); bad['episodes'].append(copy.deepcopy(bad['episodes'][0]))
    with pytest.raises(ValueError): EvidenceBatch.model_validate(bad)
    bad = batch(); bad['episodes'][0]['review_ref'] = None
    with pytest.raises(ValueError): EvidenceBatch.model_validate(bad)
    bad = batch(); bad['episodes'][0]['events'][0]['parent_ids'] = ['b']
    with pytest.raises(ValueError): EvidenceBatch.model_validate(bad)
    bad = batch(); bad['episodes'][0]['potential_loss_cents'] = 100001
    with pytest.raises(ValueError): EvidenceBatch.model_validate(bad)


def test_source_mixture_retains_unknowns_without_pooled_counts():
    req = ProjectionRequest(configuration=key(MODELS[0], 'none', False), observed_share=.5, unmodeled_mass=.1)
    b = EvidenceBatch.model_validate(batch()).model_dump(); out = project(study(), req, b)
    assert out['sources'][0]['counts']['wrong_date']['episodes'] == 4
    assert out['sources'][1]['counts']['wrong_date']['episodes'] == 2
    assert len(out['missing_source_strata']) == 7
    assert out['posterior_mean_sensitivity'][1] > out['posterior_mean_sensitivity'][0]
    assert out['model_based95_range'][1] >= .1
    assert out['sources'][1]['counts']['wrong_date']['unresolved'] == 1
    with pytest.raises(ValueError): project(study(), req, EvidenceBatch.model_validate(batch('illustration')).model_dump())
    req_all = ProjectionRequest(configuration=req.configuration, observed_share=1., unmodeled_mass=0.)
    empty = project(study(), req_all)
    assert empty['model_based95_range'] == [0., 1.] and len(empty['missing_source_strata']) == 8
    req_unknown = ProjectionRequest(configuration=req.configuration, observed_share=0., unmodeled_mass=1.)
    assert project(study(), req_unknown)['model_based95_range'] == [0., 1.]


def test_imports_and_any_projection_using_real_data_require_operator(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from app.main import create_app
    monkeypatch.setenv('RISKGRAPH_ADMIN_TOKEN', 'test-operator-private')
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'app.sqlite3'))
    client = TestClient(create_app(':memory:', seed_demo=False)); headers = {'X-Operator-Token': 'test-operator-private'}
    assert client.post('/api/evidence', json=batch()).status_code == 401
    saved = client.post('/api/evidence', json=batch(), headers=headers); assert saved.status_code == 201
    bid = saved.json()['id']
    assert client.get('/api/evidence/' + bid).status_code == 401
    assert client.get('/api/evidence/' + bid, headers=headers).json()['summary']['episodes'] == 2
    assert client.post('/api/risk-projection', json={'configuration': key(MODELS[0], 'none', False), 'batch_id': bid}).status_code == 401
    assert client.get('/api/evidence/' + '0' * 32, headers=headers).status_code == 404
    assert client.post('/api/evidence', json=batch(), headers={**headers, 'Origin': 'https://untrusted.example'}).status_code == 403
