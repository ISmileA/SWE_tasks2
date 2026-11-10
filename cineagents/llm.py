from pathlib import Path
import json, os, time, re
import httpx


class ModelRouter:
    def __init__(self,small='qwen3:0.6b',strong='qwen3:1.7b',validator='gemma3:4b'):
        self.small,self.strong,self.validator=small,strong,validator
        # Qwen3 и Qwen3.5 мы считаем одной семьёй, несмотря на разные поколения.
        family=lambda m:re.sub(r'[0-9].*$','',m.split(':')[0].lower())
        if family(validator) in {family(small),family(strong)}:
            raise ValueError('Validator must belong to another model family')

    def model(self,role,complexity='complex'):
        if role=='validator': return self.validator
        if role=='planner' and complexity=='simple': return self.small
        return self.strong


class OllamaInference:
    def __init__(self,observer,url=None):
        self.observer=observer
        self.url=url or os.environ.get('OLLAMA_URL','http://127.0.0.1:11435')
        # Мы разрешаем только локальный адрес: модель не может выбрать внешний сервер.
        from urllib.parse import urlparse
        u=urlparse(self.url)
        if u.scheme!='http' or u.hostname not in {'localhost','127.0.0.1','::1'}:
            raise ValueError('Only a local Ollama endpoint is allowed')

    def generate(self,model,system,payload,schema,trace_id):
        body={'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}],
              'format':schema,'stream':False,'options':{'temperature':0,'seed':42,'num_ctx':4096,'num_predict':256,'num_thread':6},'keep_alive':'2m'}
        if model.startswith('qwen3'): body['think']=False
        with self.observer.span('llm.generate',trace_id,model=model):
            socket_path=os.environ.get('OLLAMA_SOCKET')
            transport=httpx.HTTPTransport(uds=socket_path) if socket_path else None
            with httpx.Client(timeout=httpx.Timeout(180,connect=5),trust_env=False,transport=transport) as client:
                response=client.post(self.url+'/api/chat',json=body); response.raise_for_status()
            result=response.json()
            if not result.get('done'): raise RuntimeError('Incomplete inference response')
            if result.get('done_reason')=='length': raise RuntimeError('LLM output reached token limit')
            text=result['message']['content']
            decoded=json.loads(text)
            self.observer.metric('cineagents_llm_calls_total')
            self.observer.metric('cineagents_prompt_tokens_total',result.get('prompt_eval_count',0))
            self.observer.metric('cineagents_output_tokens_total',result.get('eval_count',0))
            self.observer.event('llm.usage',trace_id,model=model,prompt_tokens=result.get('prompt_eval_count',0),output_tokens=result.get('eval_count',0),load_duration_ns=result.get('load_duration',0),eval_duration_ns=result.get('eval_duration',0))
            return decoded


def load_instructions(role):
    base=Path(__file__).resolve().parent.parent
    paths=[base/'agent_context'/'SOUL.md',base/'agent_context'/'POLICIES.md',base/'prompts'/f'{role}.md']
    skill={'planner':'plan-recommendations','curator':'curate-catalog','validator':'verify-recommendations'}[role]
    paths.append(base/'agent_skills'/skill/'SKILL.md')
    return '\n\n'.join(path.read_text(encoding='utf-8') for path in paths)
