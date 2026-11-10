"""Через этот локальный HTTP-вход мы передаём запросы в изолированную среду по Unix-сокету."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import httpx, tempfile, os


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def proxy(self):
        length=int(self.headers.get('Content-Length',0))
        if length>16384: self.send_error(413); return
        data=self.rfile.read(length) if length else None
        path=Path(tempfile.gettempdir())/f'cineagents-{os.getuid()}'/'api'/'api.sock'
        transport=httpx.HTTPTransport(uds=str(path))
        try:
            with httpx.Client(transport=transport,timeout=600,trust_env=False) as client:
                result=client.request(self.command,'http://localhost'+self.path,content=data,headers={'Content-Type':self.headers.get('Content-Type','application/json')})
            self.send_response(result.status_code)
            self.send_header('Content-Type',result.headers.get('Content-Type','application/json'))
            self.send_header('Content-Length',str(len(result.content))); self.end_headers(); self.wfile.write(result.content)
        except httpx.HTTPError: self.send_error(503,'Sandbox API is unavailable')
    do_GET=do_POST=do_PUT=do_DELETE=proxy


if __name__=='__main__':
    ThreadingHTTPServer(('127.0.0.1',8000),Handler).serve_forever()
