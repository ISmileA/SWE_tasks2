import os,json
from pathlib import Path

rows=[]
for path in Path('/proc').iterdir():
    if not path.name.isdigit(): continue
    try:
        args=path.joinpath('cmdline').read_bytes().split(b'\0')
        args=[x.decode(errors='replace') for x in args if x]
        if args and 'bwrap' not in args[0] and any(x in args for x in ['cineagents.gateway','cineagents.api_proxy','scripts.eval_agents','cineagents.api:app','scripts.monitor']):
            rows.append({'pid':int(path.name),'args':args})
    except (OSError,PermissionError): pass
print(json.dumps(rows,indent=2))
