from pathlib import Path
import json
from cineagents.data import load_dataset, temporal_split
from cineagents.recsys import Recommender
from cineagents.memory import Memory
from cineagents.observability import Observer
from cineagents.agents import AgentSystem


def build_system():
    data=load_dataset(); train,_,_=temporal_split(data.ratings); engine=Recommender(data,train)
    checkpoint=Path('artifacts/two_tower.pt')
    if checkpoint.exists():
        from cineagents.twotower import TwoTower
        engine.neural=TwoTower.load(engine,checkpoint)
    results=Path('artifacts/recsys_results.json')
    method=json.loads(results.read_text())['selected_serving_method'] if results.exists() else 'hybrid'
    return AgentSystem(engine,Memory(),Observer(),default_method=method)
