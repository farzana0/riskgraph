"""Offline reconstruction of travel requests, synthetic costs and tail estimates."""
import argparse,json,math,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.travel import generate,outcome,checks
from app.travel_calls import payload
from app.travel_stats import analyze
from app.hardcases import digest
from app.providers import MODELS
from app.hardbench import PRICES
from scripts.travel_study import registration
from scripts.verify_research import equivalent


def verify(path):
    s=json.loads(path.read_text());assert s['status']=='complete' and s['design']==json.loads(json.dumps(registration())) and s['cases']==generate()
    cases={c['id']:c for c in s['cases']};requests=set();responses=set();identities=set();cost=0.;resolved=unknown=0
    for c in s['cases']:
        q=c['truth'];p={'action':'book','offer_id':q['valid_offer_id'],'traveller_id':c['observation']['authenticated_request']['traveller_id'],'quoted_total_cents':q['total_cents'],'reason':'Independent verification'};assert checks(c['observation'],p)['allowed']
    for row in s['cells']:
        c=cases[row['case_id']];ident=(row['case_id'],row['model']);assert ident not in identities;identities.add(ident)
        for stage in ('initial','corrected'):
            call=row[stage];o=outcome(c,call);assert o==row[stage+'_outcome'];resolved+=o['resolved'];unknown+=not o['resolved']
            if call['status']=='not_started':assert stage=='corrected' and row['initial']['status']!='complete';continue
            model=row['model'] if stage=='initial' else MODELS[1];original=row['initial']['proposal'] if stage=='corrected' else None
            key=s['design']['version']+':'+c['id']+':'+row['model']+(':'+stage if stage=='initial' else ':critic');request=payload(c['observation'],model,original);fp=digest({'key':key,'payload':request})
            assert fp==call['request_sha256'] and fp not in requests;requests.add(fp);cost+=call['estimated_cost_usd'];assert '"truth"' not in json.dumps(request)
            if call['status'] in ('complete','invalid_response'):
                assert call['response_id'] not in responses and call['response_model']==model;responses.add(call['response_id']);u=call['usage'];p=PRICES[model];assert math.isclose(call['estimated_cost_usd'],(u['input_tokens']*p[0]+u['output_tokens']*p[1])/1e6,abs_tol=1e-12)
    assert len(identities)==64 and len(requests)==s['budget']['requests_reserved'] and math.isclose(cost,s['budget']['accounted_estimated_usd'],abs_tol=1e-9) and cost<=1.2
    assert equivalent(analyze(s),s['analysis'])
    return {'cases':32,'registered_commit':'8bfdb70','requests':len(requests),'recorded_response_ids':len(responses),'resolved_stage_outcomes':resolved,'unresolved_stage_outcomes':unknown,'estimated_cost_usd':cost,'outcomes_and_total_probability_recomputed':True,'study_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(a.study);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
