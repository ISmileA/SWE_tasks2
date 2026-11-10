"""Через этот шлюз мы разрешаем изолированному процессу только ограниченные запросы к локальным моделям."""
from http.server import BaseHTTPRequestHandler
from pathlib import Path
import json, socketserver, urllib.request, urllib.error, os, tempfile, threading

MODELS={'qwen3:0.6b','qwen3:1.7b','gemma3:4b'}
INFERENCE_GATE=threading.BoundedSemaphore(1)


def validate_request(path,body):
    if path!='/api/chat': raise ValueError('Endpoint denied')
    if not isinstance(body,dict) or set(body)-{'model','messages','format','options','stream','think','keep_alive'}: raise ValueError('Unknown fields')
    if body.get('model') not in MODELS: raise ValueError('Model denied')
    if body.get('stream',False) is not False: raise ValueError('Streaming denied')
    if body.get('keep_alive','2m')!='2m': raise ValueError('Keep-alive limit')
    if 'think' in body and body['think'] is not False: raise ValueError('Unbounded reasoning denied')
    options=body.setdefault('options',{})
    bounds={'num_ctx':(1,4096,4096),'num_predict':(1,512,256),'num_thread':(1,6,6),'num_batch':(1,128,64),'seed':(0,2147483647,42)}
    if not isinstance(options,dict) or set(options)-set(bounds)-{'temperature'}: raise ValueError('Unknown inference options')
    for key,(low,high,default) in bounds.items():
        value=options.setdefault(key,default)
        if type(value) is not int or not low<=value<=high: raise ValueError(f'{key} limit')
    temperature=options.setdefault('temperature',0)
    if type(temperature) not in (int,float) or not 0<=temperature<=1: raise ValueError('Temperature limit')
    body['keep_alive']='2m';body['stream']=False


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass

    def reply(self,status,data):
        self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        if self.path!='/api/tags': return self.reply(403,b'{"error":"endpoint denied"}')
        self.forward(None)

    def do_POST(self):
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=65536: raise ValueError('Body limit')
            raw=self.rfile.read(length); body=json.loads(raw)
            validate_request(self.path,body)
        except (ValueError,TypeError,AttributeError): return self.reply(403,b'{"error":"invalid or denied request"}')
        if not INFERENCE_GATE.acquire(blocking=False): return self.reply(429,b'{"error":"inference already busy"}')
        try: self.forward(json.dumps(body).encode('utf-8'))
        finally: INFERENCE_GATE.release()

    def forward(self,raw):
        req=urllib.request.Request('http://127.0.0.1:11435'+self.path,data=raw,headers={'Content-Type':'application/json'})
        try:
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req,timeout=180) as response: self.reply(response.status,response.read(1024*1024))
        except (urllib.error.URLError,TimeoutError): self.reply(502,b'{"error":"local inference unavailable"}')


def main():
    if not hasattr(socketserver,'UnixStreamServer'): raise RuntimeError('Gateway requires Linux/WSL')
    class Server(socketserver.ThreadingMixIn,socketserver.UnixStreamServer):
        daemon_threads=True
    # Unix-сокеты мы храним в Linux: файловая система /mnt/c их не поддерживает.
    path=Path(tempfile.gettempdir())/f'cineagents-{os.getuid()}'/'gateway'/'ollama.sock'
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if path.exists():
        if not path.is_socket(): raise RuntimeError('Refusing to replace non-socket file')
        path.unlink()
    with Server(str(path),Handler) as server:
        path.chmod(0o600); print('Gateway ready',flush=True); server.serve_forever()

if __name__=='__main__': main()
