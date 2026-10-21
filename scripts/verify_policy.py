"""SMT checks of the current restricted Python gate predicates.

The translator, Python/Pydantic domain assumptions, scoring specification and
Z3 are trusted. This is not verification of the process or payment platform.
"""
import ast
import hashlib
import inspect as reflection
import json
from pathlib import Path
import random
import sys
import z3
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import domain

ROOT=Path(__file__).resolve().parents[1]
ACTIONS={'refund':0,'decline':1,'escalate':2}


def encoding():
    names=['paid','refunded','requested','amount','age','action','order','proposed_order','owner','customer']
    v={name:z3.Int(name) for name in names}
    attrs={'case.order.paid_cents':'paid','case.order.refunded_cents':'refunded',
           'case.requested_cents':'requested','proposal.amount_cents':'amount',
           'case.order.age_days':'age','proposal.action':'action','case.order.id':'order',
           'proposal.order_id':'proposed_order','case.order.owner':'owner','case.customer':'customer'}
    def expression(node):
        if isinstance(node,ast.Attribute):return v[attrs[ast.unparse(node)]]
        if isinstance(node,ast.Constant):
            if type(node.value) is int:return node.value
            if node.value in ACTIONS:return ACTIONS[node.value]
            raise ValueError('Unsupported constant')
        if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Sub):return expression(node.left)-expression(node.right)
        if isinstance(node,ast.Compare) and len(node.ops)==1:
            a,b=expression(node.left),expression(node.comparators[0]);op=node.ops[0]
            if isinstance(op,ast.Eq):return a==b
            if isinstance(op,ast.NotEq):return a!=b
            if isinstance(op,ast.Gt):return a>b
            if isinstance(op,ast.Lt):return a<b
            if isinstance(op,ast.LtE):return a<=b
            if isinstance(op,ast.GtE):return a>=b
        raise ValueError('Unsupported gate expression; update and review the translator')
    rules={};returns=0
    def walk(body,path):
        nonlocal returns
        for node in body:
            if isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str):continue
            if isinstance(node,ast.If):
                condition=expression(node.test)
                walk(node.body,z3.And(path,condition));walk(node.orelse,z3.And(path,z3.Not(condition)))
            elif isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and ast.unparse(node.value.func)=='reasons.append' and len(node.value.args)==1 and isinstance(node.value.args[0],ast.Constant):
                name=node.value.args[0].value
                if not isinstance(name,str) or name in rules:raise ValueError('Unsupported rule')
                rules[name]=path
            elif isinstance(node,ast.Return) and isinstance(node.value,ast.Dict) and z3.is_true(path):
                fields={k.value:value for k,value in zip(node.value.keys,node.value.values) if isinstance(k,ast.Constant)}
                allowed=fields.get('allowed')
                if set(fields)!={'allowed','rules','policy_version'} or ast.unparse(fields['rules'])!='reasons' or ast.unparse(fields['policy_version'])!='POLICY_VERSION':raise ValueError('Unsupported gate return fields')
                if not (isinstance(allowed,ast.UnaryOp) and isinstance(allowed.op,ast.Not) and isinstance(allowed.operand,ast.Name) and allowed.operand.id=='reasons'):
                    raise ValueError('Unsupported gate return')
                returns+=1
            else:raise ValueError('Unsupported gate statement; refusing to assert a proof')
    tree=ast.parse(reflection.getsource(domain.inspect))
    body=tree.body[0].body
    if isinstance(body[0],ast.Expr) and isinstance(body[0].value,ast.Constant) and isinstance(body[0].value.value,str):body=body[1:]
    first=body[0]
    if not (isinstance(first,ast.Assign) and len(first.targets)==1 and ast.unparse(first.targets[0])=='reasons' and isinstance(first.value,ast.List) and not first.value.elts):raise ValueError('Expected one initial empty rule list')
    if not isinstance(body[-1],ast.Return):raise ValueError('Expected one terminal gate verdict')
    walk(body[1:],z3.BoolVal(True))
    if returns!=1 or len(rules)!=8:raise ValueError('Unexpected gate structure')
    constraints=z3.And(v['paid']>=0,v['paid']<=domain.CAP,v['refunded']>=0,
                       v['requested']>=0,v['requested']<=domain.CAP,v['amount']>=0,v['amount']<=domain.CAP,
                       v['age']>=0,v['action']>=0,v['action']<=2)
    remaining=z3.If(v['paid']-v['refunded']>=0,v['paid']-v['refunded'],0)
    minimum=z3.If(v['requested']<remaining,v['requested'],remaining)
    minimum=z3.If(minimum<20000,minimum,20000)
    authority=z3.If(z3.And(v['owner']==v['customer'],v['age']<=30),minimum,0)
    excess=z3.If(v['amount']>authority,v['amount']-authority,0)
    loss=z3.If(v['action']==0,z3.If(v['order']!=v['proposed_order'],v['amount'],excess),0)
    return v,constraints,rules,loss


def concrete(values):
    action=next(k for k,a in ACTIONS.items() if a==values['action'])
    case=domain.Case(id='symbolic-witness',category='policy-proof',customer=str(values['customer']),
                    order=domain.Order(id=str(values['order']),owner=str(values['owner']),paid_cents=values['paid'],
                                       refunded_cents=values['refunded'],age_days=values['age']),
                    requested_cents=values['requested'],message='Untrusted text has no gate authority')
    proposal=domain.Proposal(action=action,order_id=str(values['proposed_order']),amount_cents=values['amount'],reason='SMT witness')
    return case,proposal


def run(samples=2000):
    v,constraints,rules,loss=encoding()
    allowed=z3.Not(z3.Or(*rules.values()))
    solver=z3.Solver();solver.set(timeout=10000)
    solver.add(constraints,allowed,loss>0)
    result=solver.check()
    if result!=z3.unsat:raise AssertionError('Gate soundness did not establish UNSAT: '+str(result))
    smt=solver.to_smt2();(ROOT/'docs/examples/policy-soundness.smt2').write_text(smt)
    ablations=[]
    for removed in ['order_mismatch','ownership','return_window','duplicate_or_excess_refund','exceeds_request','human_approval_required']:
        s=z3.Solver();s.set(timeout=10000);s.add(constraints,v['refunded']<=v['paid'],z3.Not(z3.Or(*[expr for name,expr in rules.items() if name!=removed])),loss>0)
        if s.check()!=z3.sat:raise AssertionError('Expected counterexample for missing '+removed)
        witness={name:s.model().eval(var,model_completion=True).as_long() for name,var in v.items()}
        case,proposal=concrete(witness)
        assert removed in domain.inspect(case,proposal)['rules'] and domain.score(case,proposal)>0
        ablations.append({'removed_rule':removed,'result':'sat_counterexample','witness':witness,'loss_cents':domain.score(case,proposal)})
    rng=random.Random(20261024)
    for i in range(samples):
        values={name:rng.randrange(3) for name in v}
        values.update(paid=rng.randrange(domain.CAP+1),refunded=rng.randrange(domain.CAP+100),requested=rng.randrange(domain.CAP+1),
                      amount=rng.randrange(domain.CAP+1),age=rng.randrange(90),action=rng.randrange(3))
        case,proposal=concrete(values)
        replacements=[(var,z3.IntVal(values[name])) for name,var in v.items()]
        symbolic={name:z3.is_true(z3.simplify(z3.substitute(expr,*replacements))) for name,expr in rules.items()}
        actual=domain.inspect(case,proposal)
        assert {name for name,violated in symbolic.items() if violated}==set(actual['rules'])
        assert z3.simplify(z3.substitute(loss,*replacements)).as_long()==domain.score(case,proposal)
    return {'schema_version':'policy-smt-v1','solver':z3.get_version_string(),
            'result':'unsat','property':'No schema-valid action allowed by the encoded current gate has positive specified monetary loss',
            'translation':'Restricted AST translation of app.domain.inspect, with independently encoded authorization/loss specification',
            'rules':list(rules),'differential_examples':samples,'negative_controls':ablations,
            'scope':['Trusted state, schema validity, policy specification, translator and solver are assumptions.',
                     'No end-to-end proof of Python runtime, providers, state authenticity, concurrency or payment execution.',
                     'SMT-LIB and source hashes permit reproduction; no independently checked proof certificate is claimed.'],
            'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['app/domain.py','scripts/verify_policy.py']}}


if __name__=='__main__':
    data=run();(ROOT/'docs/examples/policy-smt.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data,indent=2))
