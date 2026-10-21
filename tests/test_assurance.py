import copy
import itertools
import math
import pytest
from fastapi.testclient import TestClient
from app.assessment import AssessmentRequest, assess
from app.engine import Engine
from app.main import create_app
from app.protocol import verify_handoffs, handoff_receipts
from app.risk import conditional_mean_sequence, severity_alarm
from app.store import Store
from app.domain import CAP


def test_normal_mixture_inverts_boundary_and_zero_loss_is_uncertain():
    result = conditional_mean_sequence([0]*40)
    assert result['lower_usd'] == 0 < result['upper_usd'] < 1000
    width = result['upper_usd']/1000
    variance = 6.25+40/4
    log_e = .5*math.log(6.25/variance)+(40*width)**2/(2*variance)
    assert log_e == pytest.approx(math.log(40))
    assert not result['future_guarantee']


def test_adaptive_tree_coverage_targets_average_conditional_means():
    miss = 0
    for path in itertools.product([0,1],repeat=9):
        probability, means, losses, crossed = 1., [], [], False
        for x in path:
            p = .8 if losses and losses[-1] else .1
            probability *= p if x else 1-p
            means.append(p*1000)
            losses.append(x*CAP)
            interval = conditional_mean_sequence(losses,delta=.05)
            target = sum(means)/len(means)
            crossed |= not interval['lower_usd'] <= target <= interval['upper_usd']
        miss += probability*crossed
    assert miss <= .05


def test_loss_alarm_null_capital_and_rare_catastrophe_detection():
    capital = 0
    for path in itertools.product([0,CAP],repeat=8):
        p = .01
        probability = math.prod(p if x else 1-p for x in path)
        capital += probability*severity_alarm(path)['e_value']
    assert capital == pytest.approx(1,abs=1e-12)
    assert severity_alarm([0]*500)['alert'] is False
    assert severity_alarm([CAP, CAP]+[0]*98)['alert'] is True


def test_assessment_exact_scaling_no_storage_and_adaptive_target():
    app = create_app(':memory:',seed_demo=False)
    client = TestClient(app)
    payload = {'exposure_cap_cents':25000,'sampling':'adaptive',
               'outcomes':[{'proposed_loss_cents':25000,'residual_loss_cents':0},
                           {'proposed_loss_cents':1,'residual_loss_cents':0}]}
    result = client.post('/api/assess',json=payload)
    assert result.status_code == 200
    data = result.json()
    assert data['proposed']['observed_loss_usd'] == 250.01
    assert data['residual']['observed_loss_usd'] == 0
    assert data['residual']['expected_loss_usd'] > 0
    assert data['proposed']['anytime_upper_usd'] is None
    assert data['proposed']['conditional_mean_sequence']['upper_usd'] <= 250
    assert app.state.store.runs() == []
    assert app.state.store.attempts() == 0


@pytest.mark.parametrize('patch',[
    {'exposure_cap_cents':0}, {'outcomes':[]},
    {'outcomes':[{'proposed_loss_cents':100001,'residual_loss_cents':0}]},
    {'outcomes':[{'proposed_loss_cents':0,'residual_loss_cents':1}]},
    {'outcomes':[{'proposed_loss_cents':True,'residual_loss_cents':0}]},
    {'outcomes':[{'proposed_loss_cents':0,'residual_loss_cents':0,'customer':'private'}]},
])
def test_no_clipping_unknown_outcomes_or_private_fields(patch):
    payload={'exposure_cap_cents':CAP,'outcomes':[{'proposed_loss_cents':0,'residual_loss_cents':0}]}
    payload.update(patch)
    assert TestClient(create_app(':memory:',seed_demo=False)).post('/api/assess',json=payload).status_code==422


def test_receipts_bind_case_role_order_policy_and_payment():
    engine=Engine(Store(':memory:'))
    run=engine.create(44,1)
    event=engine.step(run['id'],0)['events'][0]
    assert verify_handoffs(event)
    for mutate in [lambda e:e['handoffs'].reverse(),
                   lambda e:e['handoffs'][1].update(capability='ledger.authorize'),
                   lambda e:e.update(seq=2),
                   lambda e:e['case'].update(customer='different'),
                   lambda e:e.update(executed_cents=99999)]:
        changed=copy.deepcopy(event)
        mutate(changed)
        assert not verify_handoffs(changed)
    forged=copy.deepcopy(event)
    forged['executed_cents']=99999
    forged['handoffs']=handoff_receipts(forged)
    assert not verify_handoffs(forged)


def test_model_pin_and_critic_attempt_accounting(monkeypatch):
    from app.providers import Agent
    monkeypatch.setenv('MAX_CLAUDE_CASES','3')
    class Paired(Agent):
        def propose(self,case,mode,memories,model=None):
            assert model=='claude-haiku-5-5'
            return super().propose(case,'offline',memories)
        def critique(self,case,proposal,memories,model=None):
            return {'recommendation':'accept','reason':'advisory','model':model}, {'input_tokens':1,'output_tokens':1}
    engine=Engine(Store(':memory:'),agent=Paired())
    run=engine.create(4,2,'claude',suite='random_stress',model='claude-haiku-5-5',advisory_critic=True)
    event=engine.step(run['id'],0)['events'][0]
    assert engine.store.attempts()==2
    assert verify_handoffs(event)
    assert len(event['handoffs'])==5
    from app.engine import BudgetExceeded
    with pytest.raises(BudgetExceeded):engine.step(run['id'],1)
    assert len(engine.store.events(run['id']))==1
    assert engine.store.attempts()==3
