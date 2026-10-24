"""Independent archive/request reconstruction; this verifier makes no provider calls."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.hardcases import digest
from app.hardbench import outcome,PRICES
from app.providers import MODELS
from app.memory_cases import generate
from app.memory_workflow import BANK,select,plan,context
from app.memory_calls import payload
from app.memory_stats import analyze,MODES
from app.record_tools import calculate
from scripts.memory_study import registration
from scripts.verify_research import equivalent


def verify(path):
    s=json.loads(path.read_text());assert s['status']=='complete'
    registered={k:v for k,v in s['design'].items() if k not in ('retrieved_memory_sha256','prepared_sha256')}
    assert registered==json.loads(json.dumps(registration()))
    assert s['cases']==generate() and digest(s['cases'])==registered['cases_sha256']
    assert digest(s['memory'])==s['design']['retrieved_memory_sha256'] and s['memory']['bank_sha256']==digest(BANK)
    assert digest(s['prepared'])==s['design']['prepared_sha256']
    for skill,source in s['memory']['skills'].items():
        expected=select(skill,{'hits':source['raw_hits'],'trace':{'traceId':source['trace_id']}})
        assert expected=={k:v for k,v in source.items() if k!='write_turn_id'}
    cases={c['id']:c for c in s['cases']}
    for case in s['cases']:
        prep=s['prepared'][case['id']];obs=case['observation'];assert prep['plan']==plan(obs)
        assert prep['selected_context']==context(obs,s['memory']) and prep['calculations']==calculate(obs)
        # Verification alone compares the public-record calculation to withheld truth.
        facts=prep['calculations']['facts'];truth=case['truth'];order=truth['order']
        assert facts['age_days']==order['age_days'] and facts['owner_account_id']==order['owner']
        assert facts['authenticated_account_id']==truth['customer']
        assert facts['remaining_usd_cents']==order['paid_cents']-order['refunded_cents']
    identities=set();requests=set();response_ids=set();cost=0.;completed=0;unresolved=0
    for cell in s['cells']:
        identity=(cell['case_id'],cell['model'],cell['memory_mode']);assert identity not in identities;identities.add(identity)
        model,mode=cell['model'],cell['memory_mode'];assert model in MODELS and mode in MODES
        case=cases[cell['case_id']];assert cell['family']==case['family'];prep=s['prepared'][case['id']]
        recalled=[] if mode=='none' else s['memory']['raw'][case['family']]['hits'] if mode=='raw' else prep['selected_context']
        calculations=prep['calculations'] if mode=='grounded' else None
        assert cell['context_sha256']==digest(recalled) and cell['calculation_sha256']==(digest(calculations) if calculations else None)
        for stage in ('initial','corrected'):
            call=cell[stage];result=cell[stage+'_outcome'];assert result==outcome(case,call)
            completed+=result['resolved'];unresolved+=not result['resolved'];assert result['residual_loss_cents'] in (None,0)
            if call['status']=='not_started':assert stage=='corrected' and cell['initial']['status']!='complete';continue
            expected_model=model if stage=='initial' else MODELS[1]
            original=cell['initial']['proposal'] if stage=='corrected' else None
            request=payload(case['observation'],recalled,expected_model,mode,calculations,original)
            key=s['design']['version']+':'+case['id']+':'+model+':'+mode+(':'+stage if stage=='initial' else ':critic')
            fingerprint=digest({'key':key,'payload':request});assert fingerprint==call['request_sha256'] and fingerprint not in requests;requests.add(fingerprint)
            assert '"truth"' not in json.dumps(request) and 'expected_refund_cents' not in json.dumps(request)
            cost+=call['estimated_cost_usd']
            if call['status'] in ('complete','invalid_response'):
                assert call['response_model']==call['model']==expected_model and call['response_id'] and call['response_id'] not in response_ids;response_ids.add(call['response_id'])
                price=PRICES[expected_model];usage=call['usage']
                assert math.isclose(call['estimated_cost_usd'],(usage['input_tokens']*price[0]+usage['output_tokens']*price[1])/1e6,abs_tol=1e-12)
    assert len(identities)==len(cases)*8 and len(requests)==s['budget']['requests_reserved']
    assert math.isclose(cost,s['budget']['accounted_estimated_usd'],abs_tol=1e-10) and cost<=6
    assert equivalent(analyze(s),s['analysis'])
    return {'schema_version':'memory-ablation-verification-v3','registered_commit':'97bc0c0','cases':len(cases),'model_strategy_cells':len(identities),
        'completed_stage_outcomes':completed,'unresolved_stage_outcomes':unresolved,'reconstructed_unique_requests':len(requests),'recorded_response_ids':len(response_ids),
        'verified_memory_skills':len(s['memory']['skills']),'rejected_retrieval_hits':sum(len(x['rejected']) for x in s['memory']['skills'].values()),
        'independently_recomputed_record_calculations':len(cases),'analysis_recomputed':True,'accounted_estimated_token_cost_usd':cost,
        'study_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'floating_tolerance':{'relative':1e-10,'absolute':1e-10},
        'scope':'Archive reconstruction verifies source selection, original request hashes, arithmetic from visible records, scoring and statistics. Recorded response IDs are provenance, not external provider certification. No provider calls are made.'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('--output',type=Path,required=True);args=p.parse_args();result=verify(args.study);args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
