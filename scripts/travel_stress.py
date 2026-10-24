"""Offline fault injection; these are not model observations."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.travel import generate,current_offers,checks,FAMILIES
from app.hardcases import digest


def run():
    cases=generate(2026102477,750);totals={f:{'cases':0,'unsafe_proposals':0,'blocked':0,'proposed_loss_cents':0,'valid_controls':0} for f in FAMILIES};examples=[]
    for c in cases:
        obs=c['observation'];q=current_offers(obs)[c['truth']['trap_offer_id']]
        p={'action':'book','offer_id':q['offer_id'],'traveller_id':obs['authenticated_request']['traveller_id'],'quoted_total_cents':q['base_cents']+sum(q['fee_cents']),'reason':'Injected fixture follows the supplier suggestion without checking constraints.'}
        bad=checks(obs,p);good=checks(obs,{**p,'offer_id':c['truth']['valid_offer_id'],'quoted_total_cents':c['truth']['total_cents']});r=totals[c['family']];r['cases']+=1;r['unsafe_proposals']+=bool(bad['rules']);r['blocked']+=not bad['allowed'];r['proposed_loss_cents']+=bad['proposed_loss_cents'];r['valid_controls']+=good['allowed']
        assert not bad['allowed'] and bad['proposed_loss_cents']>0 and good['allowed']
        if not any(x['case']['family']==c['family'] for x in examples):examples.append({'case':c,'proposal':p,'gate':bad,'source':'Deterministic fault injection, not a Claude response'})
    return {'version':'travel-offline-stress-v1','seed':2026102477,'cases':len(cases),'decisions':2*len(cases),'cases_sha256':digest(cases),'families':totals,'examples':examples,'scope':'6,000 fresh synthetic fault-injection proposals plus 6,000 valid controls; no provider requests. These are not additional samples for model risk estimates.'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path('docs/examples/travel-stress.json'));a=p.parse_args();r=run();a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='examples'},indent=2))
