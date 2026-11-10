"""Этим скриптом мы регулярно проверяем API и рекомендации. Остановка - Ctrl+C."""
import argparse,json,time,uuid
from pathlib import Path
import httpx
from cineagents.observability import Observer


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--interval',type=float,default=60);parser.add_argument('--once',action='store_true');parser.add_argument('--agent-every',type=int,default=10)
    args=parser.parse_args()
    if args.interval<5:parser.error('interval must be >=5 seconds')
    observer=Observer('runtime/monitor');iteration=0
    while True:
        trace=uuid.uuid4().hex;iteration+=1
        try:
            with observer.span('monitor.probe',trace):
                with httpx.Client(base_url='http://127.0.0.1:8000',timeout=180,trust_env=False) as client:
                    health=client.get('/health');health.raise_for_status()
                    if health.json()['status']!='ready':raise RuntimeError('degraded health')
                    rec=client.get('/recommend/10099',params={'method':'popularity','k':3});rec.raise_for_status()
                    assert len(rec.json())==3 and len({r['movie_id'] for r in rec.json()})==3
                    if args.agent_every>0 and iteration%args.agent_every==0:
                        res=client.post('/agent',json={'user_id':10099,'query':'Recommend three films','k':3});res.raise_for_status()
                        if res.json()['status']!='ok':raise RuntimeError('agent eval failed')
                observer.metric('cineagents_monitor_success_total');observer.event('monitor.health',trace,status='ready')
        except Exception as exc:
            observer.alert('monitor_unavailable',trace,{'error_type':type(exc).__name__})
        Path('runtime/monitor/latest_evidence.json').write_text(json.dumps(observer.trajectory(trace),indent=2))
        if args.once:break
        time.sleep(args.interval)

if __name__=='__main__':main()
