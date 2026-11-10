"""В этих тестах мы подменяем только внешний вызов модели, а логику системы проверяем напрямую."""
import json
from pathlib import Path
import numpy as np
import pytest
from cineagents.agents import AgentSystem, deterministic_validation
from cineagents.llm import ModelRouter
from cineagents.data import Dataset
from cineagents.recsys import Recommender
from cineagents.memory import Memory
from cineagents.observability import Observer


def test_grounding_rejects_unknown_duplicates_and_wrong_count():
    candidates=[{'movie_id':2,'genres':['Drama']},{'movie_id':3,'genres':['Drama']}]
    assert deterministic_validation([2,3],candidates,2,'Drama')==[]
    assert deterministic_validation([999,3],candidates,2,'Drama')
    assert deterministic_validation([2,2],candidates,2,'Drama')
    assert deterministic_validation([2],candidates,2,'Drama')
    assert deterministic_validation([2,3],candidates,2,'Comedy')


def test_validator_family_cannot_equal_generation_family():
    with pytest.raises(ValueError): ModelRouter(validator='qwen3:0.6b')
    with pytest.raises(ValueError): ModelRouter(strong='qwen3:1.7b',validator='qwen3.5:0.8b')
    assert ModelRouter().model('validator').startswith('gemma3:')


class ScriptedInference:
    """Эта тестовая подстановка заменяет только долгий вызов модели и не используется в приложении."""
    def __init__(self,reject=False): self.reject=reject
    def generate(self,model,system,payload,schema,trace_id):
        if 'method' in schema['properties']:
            return {'method':'popularity','genre':None}
        if 'movie_ids' in schema['properties']:
            return {'movie_ids':[r['movie_id'] for r in payload['candidates'][:payload['k']]]}
        return {'accepted':not self.reject,'issues':['fixture rejection'] if self.reject else []}


def system(tmp_path,reject=False):
    data=Dataset(np.array([[1,1,5,1],[2,2,5,2],[2,3,4,3]]),{1:'A',2:'B',3:'C'},np.ones((3,1)),['Drama'])
    return AgentSystem(Recommender(data,data.ratings),Memory(tmp_path/'m.db'),Observer(tmp_path/'obs'),inference=ScriptedInference(reject))


def test_graph_returns_grounded_results_and_stores_episode(tmp_path):
    app=system(tmp_path)
    result=app.run(1,'Recommend movies',k=2)
    assert result['status']=='ok'
    assert {r['movie_id'] for r in result['recommendations']}=={2,3}
    assert result['validator_model'].startswith('gemma')
    assert len(app.memory.episodes(1))==1
    events=[json.loads(x) for x in (tmp_path/'obs'/'events.jsonl').read_text().splitlines()]
    assert any(e['name']=='tool.recommend' for e in events)
    assert all('Recommend movies' not in json.dumps(e) for e in events)


def test_rejection_stops_after_one_repair_and_does_not_save_success(tmp_path):
    app=system(tmp_path,reject=True)
    result=app.run(1,'Recommend movies',k=2)
    assert result['status']=='rejected'
    assert result['recommendations']==[]
    assert result['repairs']==1
    assert app.memory.episodes(1)==[]


def test_inference_failure_is_observed_and_not_replaced_with_fake_answer(tmp_path):
    app=system(tmp_path)
    def fail(*args,**kwargs): raise ConnectionError('offline')
    app.inference.generate=fail
    with pytest.raises(ConnectionError): app.run(1,'Recommend',k=2)
    events=(tmp_path/'obs'/'events.jsonl').read_text()
    assert 'error' in events and 'ConnectionError' in events


def test_contradictory_validator_acceptance_does_not_release_answer(tmp_path):
    app=system(tmp_path)
    original=app.inference.generate
    def contradictory(model,system,payload,schema,trace_id):
        if 'accepted' in schema['properties']: return {'accepted':True,'issues':['unknown ID']}
        return original(model,system,payload,schema,trace_id)
    app.inference.generate=contradictory
    result=app.run(1,'Recommend movies',k=2)
    assert result['status']=='rejected' and result['recommendations']==[]
