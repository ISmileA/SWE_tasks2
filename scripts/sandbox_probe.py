"""Мы запускаем эти проверки внутри изолированной среды и пробуем запрещённые операции."""
import json, os, socket
from pathlib import Path
import httpx

checks={}
checks['host_home_absent']=not Path('/home/arseniy').exists()
checks['windows_mount_absent']=not Path('/mnt/c').exists()
try:
    Path('/app/cineagents/_probe_write').write_text('must fail')
    checks['source_readonly']=False
except OSError: checks['source_readonly']=True
try:
    socket.create_connection(('1.1.1.1',443),timeout=2)
    checks['external_network_blocked']=False
except OSError: checks['external_network_blocked']=True
transport=httpx.HTTPTransport(uds=os.environ['OLLAMA_SOCKET'])
with httpx.Client(transport=transport,base_url='http://localhost',trust_env=False) as client:
    checks['inference_gateway_reachable']=client.get('/api/tags').status_code==200
    checks['model_download_endpoint_denied']=client.post('/api/pull',json={'model':'qwen3:0.6b'}).status_code==403
checks['capabilities_dropped']='CapEff:\t0000000000000000' in Path('/proc/self/status').read_text()
checks['pid_namespace']=os.getpid()<20
result={'checks':checks,'all_passed':all(checks.values()),'pid':os.getpid(),'mount_namespace':os.readlink('/proc/self/ns/mnt'),'network_namespace':os.readlink('/proc/self/ns/net')}
Path('runtime/sandbox_evidence.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
if not result['all_passed']: raise SystemExit(1)
