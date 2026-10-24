"""Bounded real-model booking proposals; no booking tools exist."""
import json,os,time
from .hardbench import ResearchBudget
from .travel import Booking,POLICY
from .travel_calls import payload as original_payload
from .hardcases import digest
from .hardbench import PRICES
from .providers import MODELS,failure_details



class TravelBudget(ResearchBudget):
    """Atomic reservations shared by study and web workers."""
    def acquire(self,key,reserve):
        with self.lock:
            try:
                self.db.execute('BEGIN IMMEDIATE')
                old=self.db.execute('SELECT state,result FROM calls WHERE key=?',(key,)).fetchone()
                if old:
                    if old[0]=='started':raise RuntimeError('Unknown previous request; no retry')
                    result=json.loads(old[1]);self.db.commit();return result
                n,cost=self.db.execute('SELECT count(*),coalesce(sum(cost),0) FROM calls').fetchone()
                if n>=self.max_calls or cost+reserve>self.max_usd:raise RuntimeError('Travel credit allowance reached')
                self.db.execute("INSERT INTO calls VALUES (?,'started',?,NULL)",(key,reserve));self.db.commit();return None
            except BaseException:
                self.db.rollback();raise


def payload(obs,model,original=None):
    request=original_payload(obs,model,original)
    request['tool_choice']={'type':'tool','name':'propose_booking','disable_parallel_tool_use':True}
    request['max_tokens']=512
    return request


def call(agent,budget,obs,model,key,original=None):
    request=payload(obs,model,original);fingerprint=digest({'key':key,'payload':request});price=PRICES[model]
    reserve=((len(json.dumps(request).encode())+2048)*price[0]+request['max_tokens']*price[1])/1e6
    cached=budget.acquire(fingerprint,reserve)
    if cached is not None:return cached
    started=time.monotonic()
    try:
        r=agent.client.post('https://api.anthropic.com/v1/messages',headers=agent._headers(os.environ['ANTHROPIC_API_KEY']),json=request);r.raise_for_status();data=r.json();usage={k:data.get('usage',{}).get(k) for k in ('input_tokens','output_tokens')}
        if not all(type(v) is int and v>=0 for v in usage.values()):raise ValueError('Missing usage')
        blocks=[b for b in data.get('content',[]) if b.get('type')=='tool_use'];result={'status':'invalid_response','code':'incomplete_tool'}
        if data.get('stop_reason')=='tool_use' and len(blocks)==1 and blocks[0].get('name')=='propose_booking':
            try:result={'status':'complete','proposal':Booking.model_validate(blocks[0]['input']).model_dump()}
            except (ValueError,TypeError,KeyError):result={'status':'invalid_response','code':'invalid_proposal'}
        cost=(usage['input_tokens']*price[0]+usage['output_tokens']*price[1])/1e6
        result.update(model=model,response_model=data.get('model'),response_id=data.get('id'),usage=usage,estimated_cost_usd=cost,request_sha256=fingerprint,seconds=time.monotonic()-started,stop_reason=data.get('stop_reason'))
        budget.finish(fingerprint,result,cost)
    except Exception as exc:
        result={'status':'provider_error','model':model,'request_sha256':fingerprint,'estimated_cost_usd':reserve,'cost_is_reserve':True,'diagnostic':failure_details(exc,'anthropic')};budget.finish(fingerprint,result)
    return result
