"""Verify each fresh Haiku request and score from the compressed response archive."""
import argparse,gzip,hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.travel_scale import registration,generate_scale,VERSION
from app.travel_scale import summarize,analyze
from app.scale_calls import payload
from app.travel import outcome
from app.hardcases import digest
from app.hardbench import PRICES
from app.providers import MODELS
from scripts.verify_research import equivalent


def verify(summary,archive):
    s=json.loads(summary.read_text());d=s['design'];r={k:v for k,v in d.items() if k!='reference_study_sha256'};assert r==json.loads(json.dumps(registration()))
    assert d['reference_study_sha256']==hashlib.sha256((Path(__file__).resolve().parents[1]/'docs/examples/travel-v1.json').read_bytes()).hexdigest()
    cases=generate_scale();byid={c['id']:c for c in cases};raw=gzip.decompress(archive.read_bytes());assert hashlib.sha256(raw).hexdigest()==s['responses_sha256']
    rows=[json.loads(line) for line in raw.decode().splitlines()];identities=set();requests=set();responses=set();cost=0.;resolved=unknown=0
    for row in rows:
        c=byid[row['case_id']];assert row['case_id'] not in identities and row['model']==MODELS[0] and row['source']=='fresh-scale-request';identities.add(row['case_id'])
        call=row['initial'];o=outcome(c,call);assert o==row['initial_outcome'];resolved+=o['resolved'];unknown+=not o['resolved']
        request=payload(c['observation'],MODELS[0]);key=VERSION+':'+c['id']+':initial';fp=digest({'key':key,'payload':request});assert fp==call['request_sha256'] and fp not in requests;requests.add(fp)
        assert '"truth"' not in json.dumps(request) and 'valid_offer_id' not in json.dumps(request)
        cost+=call['estimated_cost_usd']
        if call['status'] in ('complete','invalid_response'):
            assert call['response_model']==call['model']==MODELS[0] and call['response_id'] and call['response_id'] not in responses;responses.add(call['response_id']);u=call['usage'];p=PRICES[MODELS[0]];assert math.isclose(call['estimated_cost_usd'],(u['input_tokens']*p[0]+u['output_tokens']*p[1])/1e6,abs_tol=1e-12)
    assert len(rows)==s['processed_cases']==s['scheduled_cases']==5504 and s['status']=='complete' and len(requests)==s['budget']['requests_reserved']
    assert math.isclose(cost,s['budget']['accounted_estimated_usd'],abs_tol=1e-9) and cost<=2
    expected=summarize(cases,rows,True);assert equivalent(expected['analysis'],s['analysis']) and expected['cases']==s['cases'] and expected['cells']==s['cells']
    for point in s['precision']:
        subset=[c for c in cases if int(c['id'].rsplit('-',1)[1])<=point['cases']//8];ids={c['id'] for c in subset};a=analyze(subset,[r for r in rows if r['case_id'] in ids])['arms'][MODELS[0]+'|0'];assert equivalent(a['tail'],point['tail']) and a['resolved']==point['resolved']
    return {'registered_commit':'644d35d','cases':len(cases),'fresh_unique_requests':len(requests),'recorded_response_ids':len(responses),'resolved_outcomes':resolved,'unresolved_outcomes':unknown,'estimated_cost_usd':cost,'request_inputs_outcomes_tail_model_and_prefixes_recomputed':True,'summary_sha256':hashlib.sha256(summary.read_bytes()).hexdigest(),'responses_sha256':s['responses_sha256'],'scope':'Audits stored response identities, source snapshots, original request hashes, scoring and interval calculations; provider identities are provenance, not external certification.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('summary',type=Path);p.add_argument('archive',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(a.summary,a.archive);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
