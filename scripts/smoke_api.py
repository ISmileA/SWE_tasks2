"""Мы проверяем запущенный HTTP API и сохраняем ответы для просмотра."""
from pathlib import Path
import json,argparse
import httpx


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--agent',action='store_true');args=parser.parse_args()
    evidence={}
    with httpx.Client(base_url='http://127.0.0.1:8000',trust_env=False,timeout=600) as client:
        response=client.get('/health'); response.raise_for_status(); evidence['health']=response.json()
        response=client.get('/recommend/1',params={'method':'two_tower','k':5}); response.raise_for_status()
        rows=response.json(); assert len(rows)==5 and len({r['movie_id'] for r in rows})==5
        evidence['two_tower_recommendations']=rows
        evidence['unknown_tool_status']=client.get('/recommend/1',params={'method':'shell'}).status_code
        assert evidence['unknown_tool_status']==400
        evidence['invalid_request_status']=client.post('/agent',json={'user_id':-1,'query':'x','k':3}).status_code
        assert evidence['invalid_request_status']==422
        evidence['metrics_status']=client.get('/metrics').status_code
        assert evidence['metrics_status']==200
        evidence['openapi_status']=client.get('/openapi.json').status_code
        assert evidence['openapi_status']==200
        user=10004
        evidence['memory_put']=client.put(f'/memory/{user}',json={'genre':'Comedy'}).status_code
        assert client.get(f'/memory/{user}').json()['preferences']['genre']['value']=='Comedy'
        if args.agent:
            response=client.post('/agent',json={'user_id':user,'query':'Recommend three comedy movies','k':3,'genre':'Comedy'});response.raise_for_status()
            evidence['agent']=response.json()
            assert evidence['agent']['status']=='ok'
            assert all('Comedy' in row['genres'] for row in evidence['agent']['recommendations'])
            trace=client.get('/traces/'+evidence['agent']['trace_id']);trace.raise_for_status()
            evidence['trace_events']=len(trace.json())
            assert evidence['trace_events']>10
            Path('artifacts/live_metrics.txt').write_text(client.get('/metrics').text)
        assert client.delete(f'/memory/{user}').status_code==200
        assert client.get(f'/memory/{user}').json()['preferences']=={}
    Path('artifacts/api_smoke.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(evidence,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
