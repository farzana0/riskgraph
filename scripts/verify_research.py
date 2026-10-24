"""Recompute the real-model study from archived synthetic inputs and responses."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.research_cases import generate,HINTS,FAMILIES,digest
from app.research_stats import analyze
from app.hardbench import outcome,MODELS,PRICES
from scripts.research_study import registration


def equivalent(a,b):
    if isinstance(a,(float,int)) and not isinstance(a,bool) and isinstance(b,(float,int)) and not isinstance(b,bool):return math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-10)
    if type(a) is not type(b):return False
    if isinstance(a,dict):return a.keys()==b.keys() and all(equivalent(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(equivalent(x,y) for x,y in zip(a,b))
    return a==b


def verify(path):
    s=json.loads(path.read_text());assert s['status']=='complete'
    design={k:v for k,v in s['design'].items() if k!='retrieved_memory_sha256'}
    assert design==json.loads(json.dumps(registration()))
    assert s['cases']==generate() and digest(s['cases'])==design['cases_sha256']
    assert digest(s['memory'])==s['design']['retrieved_memory_sha256'] and s['memory']['hint_sha256']==digest(HINTS)
    assert set(s['memory']['families'])==set(FAMILIES)
    for family,source in s['memory']['families'].items():
        assert source['trace_id'] and source['hits'] and source['prior_text']==HINTS[family]
        assert all(h['id'] and family in h['text'] and 'RGCOMPOUND20261024V2' in h['text'] for h in source['hits'])
    index={c['id']:c for c in s['cases']};cells=set();requests=set();response_ids=set();cost=0.;stages=0
    for c in s['cells']:
        identity=(c['case_id'],c['model'],c['memory']);assert identity not in cells;cells.add(identity)
        assert c['model'] in MODELS and c['family']==index[c['case_id']]['family']
        assert c['memory_trace_id']==(s['memory']['families'][c['family']]['trace_id'] if c['memory'] else None)
        for stage in ('initial','corrected'):
            call=c[stage];assert c[stage+'_outcome']==outcome(index[c['case_id']],call);stages+=1
            assert c[stage+'_outcome']['residual_loss_cents'] in (None,0)
            if 'request_sha256' not in call:assert call['status']=='not_started';continue
            assert call['request_sha256'] not in requests;requests.add(call['request_sha256']);cost+=call['estimated_cost_usd']
            if call['status']=='complete':
                assert call['response_id'] and call['response_id'] not in response_ids;response_ids.add(call['response_id'])
                expected_model=c['model'] if stage=='initial' else MODELS[1]
                assert call['model']==call['response_model']==expected_model
                usage=call['usage'];price=PRICES[expected_model]
                assert math.isclose(call['estimated_cost_usd'],(usage['input_tokens']*price[0]+usage['output_tokens']*price[1])/1e6,abs_tol=1e-12)
    assert len(cells)==len(index)*4
    assert len(requests)==s['budget']['requests_reserved']
    assert math.isclose(cost,s['budget']['accounted_estimated_usd'],abs_tol=1e-10) and cost<=5
    assert equivalent(analyze(s),s['analysis'])
    return {'schema_version':'real-memory-study-verification-v2','registered_commit':'59e57b8','cases':len(index),'model_memory_cells':len(cells),
        'recomputed_stage_outcomes':stages,'unique_model_requests':len(requests),'recorded_unique_response_ids':len(response_ids),
        'surreal_families_with_sources_and_traces':len(s['memory']['families']),'estimated_token_cost_usd':cost,
        'study_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'analysis_recomputed':True,
        'floating_point_tolerance':{'relative':1e-10,'absolute':1e-10},
        'scope':'Verifies archived synthetic scoring, case matching, request uniqueness, usage accounting, pinned source fingerprints and statistical recomputation. Response IDs are recorded provenance, not independent certification by the provider.'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    result=verify(args.study);args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
