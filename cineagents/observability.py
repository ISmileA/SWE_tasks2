"""Для наблюдения за системой мы записываем события, этапы запроса, метрики и предупреждения."""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from threading import RLock
import collections, json, time, uuid

_parent=ContextVar('span_parent',default=None)


class Observer:
    def __init__(self,path='runtime/observability'):
        self.path=Path(path); self.path.mkdir(parents=True,exist_ok=True)
        self.lock=RLock(); self.counters=collections.Counter(); self.values=collections.defaultdict(list)

    def event(self,name,trace_id,**attributes):
        row={'time':time.time(),'name':name,'trace_id':trace_id,**attributes}
        with self.lock:
            with (self.path/'events.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(row,ensure_ascii=False)+'\n')

    def metric(self,name,value=1):
        with self.lock:
            self.counters[name]+=value

    def alert(self,name,trace_id,detail):
        row={'time':time.time(),'name':name,'trace_id':trace_id,'detail':detail}
        with self.lock:
            with (self.path/'alerts.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(row)+'\n')

    @contextmanager
    def span(self,name,trace_id,**attributes):
        sid=uuid.uuid4().hex; parent=_parent.get(); token=_parent.set(sid); start=time.perf_counter()
        status='ok'; error=None
        try: yield sid
        except Exception as exc:
            status='error'; error=type(exc).__name__
            self.metric('cineagents_errors_total'); self.alert('span_failure',trace_id,{'span':name,'error_type':error})
            raise
        finally:
            elapsed=time.perf_counter()-start; _parent.reset(token)
            with self.lock:
                self.values[name].append(elapsed)
                # Мы ограничиваем размер истории времени выполнения, чтобы она не росла бесконечно.
                if len(self.values[name])>1000: self.values[name]=self.values[name][-1000:]
            self.event(name,trace_id,span_id=sid,parent_span_id=parent,status=status,error_type=error,duration_seconds=elapsed,attributes=attributes)
            if name=='agent.run' and elapsed>120: self.alert('agent_latency',trace_id,{'seconds':elapsed,'threshold':120})

    def trajectory(self,trace_id):
        path=self.path/'events.jsonl'
        if not path.exists(): return []
        with self.lock: rows=path.read_text(encoding='utf-8').splitlines()
        return [row for line in rows if (row:=json.loads(line)).get('trace_id')==trace_id]

    def prometheus(self):
        with self.lock:
            lines=[f'{k} {v}' for k,v in sorted(self.counters.items())]
            for name,values in sorted(self.values.items()):
                safe=name.replace('.','_')
                lines.extend([f'cineagents_duration_seconds_count{{stage="{safe}"}} {len(values)}',f'cineagents_duration_seconds_sum{{stage="{safe}"}} {sum(values)}'])
        return '\n'.join(lines)+'\n'
