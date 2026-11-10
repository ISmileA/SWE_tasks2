"""Здесь мы задаём локальный API. user_id служит для демонстрации и не заменяет вход в систему."""
from contextlib import asynccontextmanager
from threading import BoundedSemaphore
import re, os
import httpx
import psutil
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, ConfigDict
from cineagents.service import build_system


@asynccontextmanager
async def lifespan(app):
    app.state.system=build_system(); app.state.gate=BoundedSemaphore(1)
    yield


app=FastAPI(title='CineAgents',description='Учебная локальная MAS и RecSys. Идентификатор пользователя демонстрационный; слушать только localhost.',lifespan=lifespan)


class AgentRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    user_id:int=Field(ge=1,strict=True)
    query:str=Field(min_length=1,max_length=2000)
    k:int=Field(default=5,ge=1,le=10,strict=True)
    genre:str|None=None


class Preference(BaseModel):
    model_config=ConfigDict(extra='forbid')
    genre:str


@app.get('/health')
def health():
    system=app.state.system
    try:
        transport=httpx.HTTPTransport(uds=os.environ['OLLAMA_SOCKET']) if os.environ.get('OLLAMA_SOCKET') else None
        with httpx.Client(timeout=3,trust_env=False,transport=transport) as client:
            response=client.get(system.inference.url+'/api/tags'); response.raise_for_status()
        names={m['name'] for m in response.json()['models']}
        missing={system.router.small,system.router.strong,system.router.validator}-names
    except (httpx.HTTPError,KeyError,ValueError): missing={system.router.small,system.router.strong,system.router.validator}
    return {'status':'ready' if not missing else 'degraded','missing_models':sorted(missing),'neural_loaded':system.engine.neural is not None,'catalogue_size':system.engine.n,'rss_bytes':psutil.Process().memory_info().rss}


@app.get('/recommend/{user_id}')
def recommend(user_id:int,method:str='hybrid',k:int=Query(default=5,ge=1,le=100),genre:str|None=None):
    try: return app.state.system.engine.recommend(user_id,method,k,genre)
    except (ValueError,RuntimeError) as e: raise HTTPException(400,str(e)) from e


@app.post('/agent')
def agent(request:AgentRequest):
    if not app.state.gate.acquire(blocking=False): raise HTTPException(429,'One local inference workflow is already running')
    try: return app.state.system.run(**request.model_dump())
    except ValueError as e: raise HTTPException(422,str(e)) from e
    except (httpx.HTTPError,RuntimeError) as e: raise HTTPException(503,'Local inference failed; inspect observability logs') from e
    finally: app.state.gate.release()


@app.put('/memory/{user_id}')
def preference(user_id:int,request:Preference):
    if user_id<1 or request.genre not in app.state.system.engine.dataset.genres: raise HTTPException(422,'Invalid user or genre')
    app.state.system.memory.set_preference(user_id,'genre',request.genre,'explicit API preference')
    return {'status':'saved'}


@app.get('/memory/{user_id}')
def read_memory(user_id:int):
    return {'preferences':app.state.system.memory.preferences(user_id),'episodes':app.state.system.memory.episodes(user_id)}


@app.delete('/memory/{user_id}')
def delete_memory(user_id:int):
    app.state.system.memory.delete_user(user_id); return {'status':'deleted'}


@app.get('/metrics',response_class=PlainTextResponse)
def metrics():
    return app.state.system.observer.prometheus()+f'cineagents_process_rss_bytes {psutil.Process().memory_info().rss}\n'


@app.get('/traces/{trace_id}')
def trace(trace_id:str):
    if not re.fullmatch('[a-f0-9]{32}',trace_id): raise HTTPException(422,'Invalid trace identifier')
    return app.state.system.observer.trajectory(trace_id)
