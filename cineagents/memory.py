"""В памяти мы разделяем пользователей и сохраняем только явно заданные предпочтения."""
import json
import sqlite3
import time
from pathlib import Path


class Memory:
    def __init__(self,path='runtime/memory.db'):
        self.path=str(path)
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as c:
            c.execute('PRAGMA journal_mode=WAL')
            c.executescript('''CREATE TABLE IF NOT EXISTS preferences(
                user_id INTEGER, key TEXT, value TEXT, source TEXT,
                updated REAL, expires REAL, PRIMARY KEY(user_id,key));
                CREATE TABLE IF NOT EXISTS episodes(
                id INTEGER PRIMARY KEY, user_id INTEGER, payload TEXT,
                created REAL, expires REAL);''')

    def connect(self): return sqlite3.connect(self.path,timeout=30)

    def set_preference(self,user_id,key,value,source,ttl=90*86400,now=None):
        now=time.time() if now is None else now
        if not key or not source or ttl<=0: raise ValueError('Key, provenance and positive TTL required')
        with self.connect() as c:
            c.execute('INSERT INTO preferences VALUES(?,?,?,?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value,source=excluded.source,updated=excluded.updated,expires=excluded.expires',
                      (user_id,key,json.dumps(value,ensure_ascii=False),source,now,now+ttl))

    def preferences(self,user_id,now=None):
        now=time.time() if now is None else now
        with self.connect() as c:
            c.execute('DELETE FROM preferences WHERE expires<=?',(now,))
            rows=c.execute('SELECT key,value,source,updated,expires FROM preferences WHERE user_id=?',(user_id,)).fetchall()
        return {k:{'value':json.loads(v),'source':s,'updated':u,'expires':e} for k,v,s,u,e in rows}

    def add_episode(self,user_id,payload,ttl=7*86400,now=None):
        now=time.time() if now is None else now
        if ttl<=0: raise ValueError('Positive TTL required')
        with self.connect() as c:
            c.execute('INSERT INTO episodes(user_id,payload,created,expires) VALUES(?,?,?,?)',(user_id,json.dumps(payload,ensure_ascii=False),now,now+ttl))

    def episodes(self,user_id,limit=5,now=None):
        now=time.time() if now is None else now
        with self.connect() as c:
            c.execute('DELETE FROM episodes WHERE expires<=?',(now,))
            rows=c.execute('SELECT payload FROM episodes WHERE user_id=? ORDER BY created DESC,id DESC LIMIT ?',(user_id,max(0,min(limit,20)))).fetchall()
        return [json.loads(r[0]) for r in rows]

    def delete_user(self,user_id):
        with self.connect() as c:
            for table in ('preferences','episodes'): c.execute(f'DELETE FROM {table} WHERE user_id=?',(user_id,))
