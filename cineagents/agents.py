from __future__ import annotations
from typing import TypedDict
import hashlib, uuid
from pydantic import BaseModel, ConfigDict, StrictInt, StrictBool
from langgraph.graph import StateGraph, START, END
from cineagents.llm import ModelRouter, OllamaInference, load_instructions
from cineagents.decision import DecisionModel
from cineagents.recsys import METHODS


class Selection(BaseModel):
    model_config=ConfigDict(extra='forbid')
    movie_ids:list[StrictInt]


class Judgement(BaseModel):
    model_config=ConfigDict(extra='forbid')
    accepted:StrictBool
    issues:list[str]


class State(TypedDict,total=False):
    user_id:int
    query:str
    k:int
    requested_genre:str|None
    trace_id:str
    route:dict
    plan:dict
    candidates:list
    selected:list[int]
    issues:list[str]
    accepted:bool
    repairs:int
    planner_model:str
    result:dict
    memories:dict


def deterministic_validation(ids,candidates,k,genre):
    errors=[]; by_id={r['movie_id']:r for r in candidates}
    if len(ids)!=k: errors.append('wrong_count')
    if any(type(i) is not int for i in ids): errors.append('non_integer_id')
    if len(set(ids))!=len(ids): errors.append('duplicates')
    if any(i not in by_id for i in ids): errors.append('unknown_id')
    if genre and any(genre not in by_id[i]['genres'] for i in ids if i in by_id): errors.append('genre_mismatch')
    return errors


class AgentSystem:
    def __init__(self,engine,memory,observer,inference=None,router=None,decision=None,default_method='hybrid'):
        self.engine,self.memory,self.observer=engine,memory,observer
        self.router=router or ModelRouter(); self.inference=inference or OllamaInference(observer)
        self.decision=decision or DecisionModel(); self.default_method=default_method
        self.instructions={role:load_instructions(role) for role in ('planner','curator','validator')}
        graph=StateGraph(State)
        for name in ['gate','planner','retrieve','curator','validator','finalize']: graph.add_node(name,getattr(self,name))
        graph.add_edge(START,'gate')
        graph.add_conditional_edges('gate',lambda s:'finalize' if s['route']['route']=='unsafe' else 'planner')
        graph.add_edge('planner','retrieve'); graph.add_edge('retrieve','curator'); graph.add_edge('curator','validator')
        graph.add_conditional_edges('validator',lambda s:'finalize' if s['accepted'] or s['repairs']>=1 else 'curator')
        graph.add_edge('finalize',END)
        self.graph=graph.compile()

    def gate(self,s):
        with self.observer.span('decision.route',s['trace_id']): route=self.decision.decide(s['query'])
        self.observer.event('routing.decision',s['trace_id'],**route)
        memories={'preferences':self.memory.preferences(s['user_id']),'episodes':self.memory.episodes(s['user_id'])}
        return {'route':route,'memories':memories,'accepted':False,'repairs':0,'issues':['out_of_scope'] if route['route']=='unsafe' else []}

    def planner(self,s):
        model=self.router.model('planner',s['route']['route'])
        methods=[m for m in METHODS if m!='two_tower' or self.engine.neural is not None]
        schema={'type':'object','properties':{'method':{'type':'string','enum':methods},'genre':{'anyOf':[{'type':'string','enum':self.engine.dataset.genres},{'type':'null'}]}},'required':['method','genre'],'additionalProperties':False}
        stored=s['memories']['preferences'].get('genre',{}).get('value')
        payload={'query':s['query'],'requested_genre':s['requested_genre'],'stored_genre':stored,'default_method':self.default_method,
                 'recent_recommendations':[e.get('movie_ids',[]) for e in s['memories']['episodes']]}
        with self.observer.span('agent.planner',s['trace_id'],model=model):
            plan=self.inference.generate(model,self.instructions['planner'],payload,schema,s['trace_id'])
            if set(plan)!={'method','genre'} or plan['method'] not in methods or (plan['genre'] is not None and plan['genre'] not in self.engine.dataset.genres):
                raise ValueError('Invalid plan')
            if s['requested_genre'] is not None and plan['genre']!=s['requested_genre']: raise ValueError('Explicit genre was not preserved')
        return {'plan':plan,'planner_model':model}

    def retrieve(self,s):
        with self.observer.span('tool.recommend',s['trace_id'],method=s['plan']['method']):
            candidates=self.engine.recommend(s['user_id'],s['plan']['method'],min(100,max(12,s['k']*3)),s['plan']['genre'])
            recent={i for e in s['memories']['episodes'] for i in e.get('movie_ids',[])}
            fresh=[r for r in candidates if r['movie_id'] not in recent]
            if len(fresh)>=s['k']: candidates=fresh
            if len(candidates)<s['k']: raise ValueError('Not enough eligible catalogue items')
        self.observer.metric('cineagents_tool_success_total')
        self.observer.event('tool.result',s['trace_id'],movie_ids=[r['movie_id'] for r in candidates],method=s['plan']['method'],genre=s['plan']['genre'])
        return {'candidates':candidates}

    def curator(self,s):
        model=self.router.model('curator')
        schema={'type':'object','properties':{'movie_ids':{'type':'array','items':{'type':'integer','enum':[r['movie_id'] for r in s['candidates']]},'minItems':s['k'],'maxItems':s['k']}},'required':['movie_ids'],'additionalProperties':False}
        payload={'query':s['query'],'k':s['k'],'genre':s['plan']['genre'],'candidates':s['candidates'],'repair_feedback':s['issues']}
        with self.observer.span('agent.curator',s['trace_id'],model=model):
            value=self.inference.generate(model,self.instructions['curator'],payload,schema,s['trace_id'])
            selection=Selection.model_validate(value)
        return {'selected':selection.movie_ids,'repairs':s['repairs']+int(bool(s['issues']))}

    def validator(self,s):
        model=self.router.model('validator')
        errors=deterministic_validation(s['selected'],s['candidates'],s['k'],s['plan']['genre'])
        payload={'expected_count':s['k'],'selected_count':len(s['selected']),'unique_count':len(set(s['selected'])),
                 'selected_ids':s['selected'],'allowed_ids':[r['movie_id'] for r in s['candidates']],
                 'deterministic_checks_passed':not errors,'failed_checks':errors}
        with self.observer.span('agent.validator',s['trace_id'],model=model):
            raw=self.inference.generate(model,self.instructions['validator'],payload,Judgement.model_json_schema(),s['trace_id'])
            judgement=Judgement.model_validate(raw)
        accepted=judgement.accepted and not errors and not judgement.issues
        if not accepted:
            self.observer.metric('cineagents_validation_rejections_total')
            self.observer.alert('validation_rejected',s['trace_id'],{'deterministic_issues':errors,'model_accepted':judgement.accepted})
        self.observer.event('validation.decision',s['trace_id'],model=model,accepted=accepted,deterministic_issues=errors,model_issues=judgement.issues)
        return {'accepted':accepted,'issues':errors+judgement.issues or ([] if accepted else ['validator_rejected'])}

    def finalize(self,s):
        by_id={r['movie_id']:r for r in s.get('candidates',[])}
        rows=[by_id[i] for i in s.get('selected',[])] if s['accepted'] else []
        for row in rows:
            row['explanation']=f"Каталог MovieLens: {', '.join(row['genres'])}; метод {row['method']}."
        result={'status':'ok' if s['accepted'] else 'rejected','trace_id':s['trace_id'],'recommendations':rows,
                'plan':s.get('plan'),'planner_model':s.get('planner_model'),'curator_model':self.router.strong if s.get('selected') else None,
                'validator_model':self.router.validator if s.get('selected') else None,'repairs':s['repairs'],'issues':s['issues'],'routing':s['route']}
        if s['accepted']:
            self.memory.add_episode(s['user_id'],{'movie_ids':s['selected'],'method':s['plan']['method'],'trace_id':s['trace_id']})
            self.observer.metric('cineagents_success_total'); self.observer.metric('cineagents_impressions_total',len(rows))
        return {'result':result}

    def run(self,user_id,query,k=5,genre=None):
        if type(user_id) is not int or user_id<1: raise ValueError('Positive user_id required')
        if not isinstance(query,str) or not query.strip() or len(query)>2000: raise ValueError('Query must be 1..2000 characters')
        if type(k) is not int or not 1<=k<=10: raise ValueError('k must be 1..10')
        if genre is not None and genre not in self.engine.dataset.genres: raise ValueError('Unknown genre')
        trace_id=uuid.uuid4().hex
        self.observer.metric('cineagents_requests_total')
        with self.observer.span('agent.run',trace_id,query_sha256=hashlib.sha256(query.encode()).hexdigest(),query_length=len(query)):
            result=self.graph.invoke({'user_id':user_id,'query':query,'k':k,'requested_genre':genre,'trace_id':trace_id},{'recursion_limit':15})
        return result['result']
