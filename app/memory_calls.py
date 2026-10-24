"""Versioned caller for the new memory protocol; immutable legacy caller is retained."""
import json
import os
import time
from .domain import Proposal
from .hardcases import POLICY,digest
from .hardbench import PRICES,response_schema
from .providers import MODELS,failure_details
from .memory_workflow import USE_CONTRACT


def payload(observation,memory,model,mode,calculations=None,original=None):
    system=POLICY
    if mode in ('selected','grounded'):system+=' '+USE_CONTRACT
    content={'task':observation,'recalled_prior_experience':memory}
    if calculations is not None:content['record_calculations']=calculations
    if original is not None:
        content['untrusted_initial_proposal']=original
        system+=' You are a corrective critic in a separate model request. Recompute from current records. Preserve a correct proposal or revise it. Do not assume the first agent or memory is correct. You cannot authorize payment.'
    return {'model':model,'max_tokens':2048,'system':system,'messages':[{'role':'user','content':json.dumps(content,ensure_ascii=False)}],
        'tools':[{'name':'propose_refund','description':'One synthetic proposal; no payment authority','strict':True,'input_schema':response_schema()}],
        'tool_choice':{'type':'auto','disable_parallel_tool_use':True},'thinking':{'type':'disabled' if model==MODELS[0] else 'between_tools'},'output_config':{'effort':'low'}}


def call(agent,budget,request,key):
    model=request['model'];reserve=((len(json.dumps(request,ensure_ascii=False).encode())+2048)*PRICES[model][0]+request['max_tokens']*PRICES[model][1])/1e6
    fingerprint=digest({'key':key,'payload':request});cached=budget.acquire(fingerprint,reserve)
    if cached is not None:return cached
    started=time.monotonic()
    try:
        response=agent.client.post('https://api.anthropic.com/v1/messages',headers=agent._headers(os.environ['ANTHROPIC_API_KEY']),json=request);response.raise_for_status();data=response.json();usage=data.get('usage',{})
        if not all(type(usage.get(k)) is int and usage[k]>=0 for k in ('input_tokens','output_tokens')):raise ValueError('Usage unavailable')
        usage={k:usage[k] for k in ('input_tokens','output_tokens')};cost=(usage['input_tokens']*PRICES[model][0]+usage['output_tokens']*PRICES[model][1])/1e6
        blocks=[b for b in data.get('content',[]) if b.get('type')=='tool_use'];result={'status':'invalid_response','code':'incomplete_tool'}
        if data.get('stop_reason')=='tool_use' and len(blocks)==1 and blocks[0].get('name')=='propose_refund':
            try:result={'status':'complete','proposal':Proposal.model_validate(blocks[0]['input']).model_dump()}
            except (ValueError,TypeError,KeyError):result={'status':'invalid_response','code':'proposal_schema'}
        result.update(model=model,usage=usage,estimated_cost_usd=cost,seconds=time.monotonic()-started,request_sha256=fingerprint,stop_reason=data.get('stop_reason'),response_id=data.get('id'),response_model=data.get('model'))
        budget.finish(fingerprint,result,cost)
    except Exception as exc:
        result={'status':'provider_error','diagnostic':failure_details(exc,'anthropic'),'model':model,'seconds':time.monotonic()-started,'estimated_cost_usd':reserve,'cost_is_reserve':True,'request_sha256':fingerprint};budget.finish(fingerprint,result)
    return result
