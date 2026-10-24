"""Recompute fresh-study provenance, paired outcomes, intervals and prefixes offline."""
import argparse,hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.followup_cases import generate
from app.followup_stats import analyze,precision,MODES
from app.memory_workflow import context,plan
from app.record_tools import calculate
from app.memory_calls import payload
from app.hardcases import digest
from app.hardbench import outcome,PRICES
from app.providers import MODELS
from scripts.followup_study import registration
from scripts.verify_research import equivalent


def verify(path):
    s=json.loads(path.read_text());assert s['status']=='complete';d=s['design'];r={k:v for k,v in d.items() if k!='prepared_sha256'}
    assert r==json.loads(json.dumps(registration(d['per_family'],d['max_usd'])))
    assert s['cases']==generate(d['per_family']) and digest(s['memory'])==d['retrieved_memory_sha256'] and digest(s['prepared'])==d['prepared_sha256']
    cases={c['id']:c for c in s['cases']};identities=set();requests=set();responses=set();cost=0.;resolved=unknown=0
    for c in s['cases']:
        p=s['prepared'][c['id']];assert p=={'plan':plan(c['observation']),'selected_context':context(c['observation'],s['memory']),'calculations':calculate(c['observation'])}
        o=c['truth']['order'];f=p['calculations']['facts'];assert f['age_days']==o['age_days'] and f['remaining_usd_cents']==o['paid_cents']-o['refunded_cents']
    for cell in s['cells']:
        ident=(cell['case_id'],cell['model'],cell['memory_mode']);assert ident not in identities;identities.add(ident)
        c=cases[cell['case_id']];model,mode=cell['model'],cell['memory_mode'];assert model in MODELS and mode in MODES
        memory=[] if mode=='none' else s['prepared'][c['id']]['selected_context'];assert cell['context_sha256']==digest(memory) and cell['calculation_sha256'] is None
        for stage in ('initial','corrected'):
            call=cell[stage];o=outcome(c,call);assert o==cell[stage+'_outcome'];resolved+=o['resolved'];unknown+=not o['resolved']
            if call['status']=='not_started':assert stage=='corrected' and cell['initial']['status']!='complete';continue
            m=model if stage=='initial' else MODELS[1];original=cell['initial']['proposal'] if stage=='corrected' else None
            request=payload(c['observation'],memory,m,mode,original=original);key=d['version']+':'+c['id']+':'+model+':'+mode+(':'+stage if stage=='initial' else ':critic');fp=digest({'key':key,'payload':request})
            assert fp==call['request_sha256'] and fp not in requests;requests.add(fp);cost+=call['estimated_cost_usd']
            assert 'record_calculations' not in request['messages'][0]['content'] and '"truth"' not in json.dumps(request)
            if call['status'] in ('complete','invalid_response'):
                assert call['response_id'] not in responses and call['response_model']==m;responses.add(call['response_id']);u=call['usage'];p=PRICES[m];assert math.isclose(call['estimated_cost_usd'],(u['input_tokens']*p[0]+u['output_tokens']*p[1])/1e6,abs_tol=1e-12)
    assert len(identities)==len(cases)*4 and len(requests)==s['budget']['requests_reserved'] and math.isclose(cost,s['budget']['accounted_estimated_usd'],abs_tol=1e-9) and cost<=d['max_usd']
    assert equivalent(analyze(s),s['analysis']) and equivalent(precision(s),s['precision'])
    return {'cases':len(cases),'registered_commit':'a308ec6','requests':len(requests),'recorded_response_ids':len(responses),'resolved_stage_outcomes':resolved,'unresolved_stage_outcomes':unknown,'estimated_cost_usd':cost,'analysis_and_prefixes_recomputed':True,'study_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(a.study);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
