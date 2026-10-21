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
    {'outcomes':[{'proposed_loss_cents':0,'residual_loss_cents':100001}]},
    {'outcomes':[{'proposed_loss_cents':True,'residual_loss_cents':0}]},
    {'outcomes':[{'proposed_loss_cents':0,'residual_loss_cents':0,'customer':'private'}]},
])
def test_no_clipping_unknown_outcomes_or_private_fields(patch):
    payload={'exposure_cap_cents':CAP,'outcomes':[{'proposed_loss_cents':0,'residual_loss_cents':0}]}
    payload.update(patch)
    assert TestClient(create_app(':memory:',seed_demo=False)).post('/api/assess',json=payload).status_code==422


def test_execution_failures_may_introduce_loss_after_a_correct_proposal():
    result=assess(AssessmentRequest(exposure_cap_cents=10000,
                  outcomes=[{'proposed_loss_cents':0,'residual_loss_cents':2500}]))
    assert result['execution_loss_increases']==1
    assert result['proposed']['observed_loss_usd']==0
    assert result['residual']['observed_loss_usd']==25


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


def test_zero_difference_analysis_retains_uncertainty():
    import importlib.util
    from pathlib import Path
    from app.domain import Proposal
    spec=importlib.util.spec_from_file_location('paired_analysis',Path(__file__).parents[1]/'scripts/analyze_paired.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    class Safe:
        def propose(self,case,mode,memories):
            return Proposal(action='escalate',order_id=case.order.id,amount_cents=0,reason='test'),{}
    engine=Engine(Store(':memory:'),agent=Safe())
    models=['claude-haiku-5-5','claude-sonnet-5-5'];cells=[];snapshots={}
    for model in models:
        run=engine.create(77,3)
        for i in range(3):snapshot=engine.step(run['id'],i)
        cells.append({'seed':77,'model':model,'run_id':run['id'],'status':'complete'})
        snapshots[run['id']]=snapshot
    result=module.analyze({'status':'complete','cells':cells,'models':models,'seeds':[77]},snapshots)
    difference=result['difference']
    assert difference['observed_mean_difference_usd']==0
    assert difference['conditional_difference_interval_usd'][0]<0<difference['conditional_difference_interval_usd'][1]
    assert difference['bootstrap_degenerate']
    assert all(row['streams']['proposed']['posterior_mean_usd']>0 for row in result['models'])


def test_operational_evidence_distinguishes_unresolved_and_execution_loss():
    client=TestClient(create_app(':memory:',seed_demo=False))
    study=client.get('/api/operational').json()['study']
    assert study['provider_requests']==0
    assert len(study['scenarios'])==12
    assert study['unresolved_episodes']==2000
    example=client.get('/api/operational/example').json()
    assert len(example)==1000
    result=client.post('/api/assess',json={'exposure_cap_cents':CAP,'sampling':'adaptive',
                       'outcomes':[{k:r[k] for k in ('proposed_loss_cents','residual_loss_cents')} for r in example]}).json()
    assert result['proposed']['observed_loss_usd']==0
    assert result['residual']['observed_loss_usd']==750
    assert result['execution_loss_increases']==30


def test_symbolic_current_gate_cannot_allow_positive_specified_loss():
    import z3
    from scripts.verify_policy import encoding
    variables,constraints,rules,loss=encoding()
    solver=z3.Solver()
    solver.add(constraints,z3.Not(z3.Or(*rules.values())),loss>0)
    assert solver.check()==z3.unsat


def test_symbolic_translator_rejects_rule_list_reset(monkeypatch):
    import inspect
    import scripts.verify_policy as verification
    original=inspect.getsource(verification.domain.inspect)
    changed=original.replace('    if proposal.action == "refund":','    if proposal.action == "refund":\n        reasons = []')
    assert changed!=original
    monkeypatch.setattr(verification.reflection,'getsource',lambda _:changed)
    with pytest.raises(ValueError,match='Unsupported gate statement'):
        verification.encoding()


@pytest.mark.parametrize('length,valid',[(1,True),(600,True),(0,False),(1001,False)])
def test_critic_contract_explains_and_enforces_reason_limit(monkeypatch,case,length,valid):
    import httpx,json
    from app.domain import Proposal
    from app.providers import Agent,ProviderError
    monkeypatch.setenv('ANTHROPIC_API_KEY','test-key')
    monkeypatch.setenv('ANTHROPIC_WORKSPACE_ID','wrkspc_test')
    def handler(request):
        payload=json.loads(request.content)
        assert '600 characters' in payload['system']
        assert '600' in payload['tools'][0]['input_schema']['properties']['reason']['description']
        return httpx.Response(200,json={'stop_reason':'tool_use','content':[{'type':'tool_use','name':'review_proposal','input':{'recommendation':'accept','reason':'x'*length}}],'usage':{'input_tokens':1,'output_tokens':2}})
    agent=Agent(httpx.Client(transport=httpx.MockTransport(handler)))
    proposal=Proposal(action='escalate',order_id=case.order.id,amount_cents=0,reason='test')
    if valid:assert agent.critique(case,proposal,[])[0]['authority']=='advisory_only'
    else:
        with pytest.raises(ProviderError):agent.critique(case,proposal,[])


def test_critic_schema_failure_executes_nothing_and_counts_both_requests(monkeypatch):
    import httpx,json
    from app.providers import Agent,ProviderError
    monkeypatch.setenv('ANTHROPIC_API_KEY','test-key')
    monkeypatch.setenv('ANTHROPIC_WORKSPACE_ID','wrkspc_test')
    def handler(request):
        payload=json.loads(request.content);tool=payload['tools'][0]['name']
        if tool=='propose_refund':
            c=json.loads(payload['messages'][0]['content'])
            result={'action':'escalate','order_id':c['trusted_order']['id'],'amount_cents':0,'reason':'review'}
        else:result={'recommendation':'accept','reason':'x'*1001}
        return httpx.Response(200,json={'stop_reason':'tool_use','content':[{'type':'tool_use','name':tool,'input':result}],'usage':{}})
    engine=Engine(Store(':memory:'),agent=Agent(httpx.Client(transport=httpx.MockTransport(handler))))
    run=engine.create(41,1,'claude',advisory_critic=True)
    with pytest.raises(ProviderError):engine.step(run['id'],0)
    assert engine.store.attempts()==2
    assert engine.store.events(run['id'])==[]
    assert engine.store.db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0]==0


def test_retry_retains_aborted_evidence_and_disables_fixed_tail_claim():
    from app.domain import Proposal
    from app.providers import ProviderError
    class Flaky:
        failed=False
        def propose(self,case,mode,memories):
            if not self.failed:
                self.failed=True
                raise ProviderError('Invalid structured response')
            return Proposal(action='escalate',order_id=case.order.id,amount_cents=0,reason='review'),{}
    engine=Engine(Store(':memory:'),agent=Flaky())
    run=engine.create(4,1)
    with pytest.raises(ProviderError):engine.step(run['id'],0)
    result=engine.step(run['id'],0)
    assert result['run']['status']=='complete'
    assert result['quality']['aborted_attempts']==1
    assert result['run']['aborted_attempts'][0]['outcome']=='not_scored_no_execution'
    assert result['gross']['anytime_upper_usd'] is None
    assert result['gross']['conditional_mean_sequence']['future_guarantee'] is False
