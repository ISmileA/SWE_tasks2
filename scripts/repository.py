"""Для публикации мы используем существующую авторизацию Git, не выводя секреты в журнал."""
import argparse,json,os,subprocess,urllib.request,urllib.error
from pathlib import Path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--create',action='store_true');args=parser.parse_args()
    env=os.environ.copy()
    env.update(GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='never',GCM_GUI_PROMPT='false')
    for key in list(env):
        if key.startswith('GIT_TRACE'): env.pop(key)
    command=['git','-c','safe.directory=C:/KFU/DM/Task2','credential','fill']
    try: proc=subprocess.run(command,input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,timeout=25,env=env)
    except subprocess.TimeoutExpired:
        print('No noninteractive GitHub credential available');return
    values=dict(line.split('=',1) for line in proc.stdout.splitlines() if '=' in line)
    secret=values.get('password')
    status={'authenticated':False,'created':False,'url':None}
    if secret:
        def api(path,data=None):
            headers={'Authorization':'Bearer '+secret,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'CineAgents-course-project'}
            req=urllib.request.Request('https://api.github.com'+path,headers=headers,data=json.dumps(data).encode() if data is not None else None)
            with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
        try:
            user=api('/user')['login'];status.update(authenticated=True,login=user)
            name='cineagents-kfu-2026'
            try: repo=api(f'/repos/{user}/{name}')
            except urllib.error.HTTPError as exc:
                if exc.code!=404: raise
                repo=None
            if repo: status.update(url=repo['html_url'],created=True,private=repo['private'])
            elif args.create:
                repo=api('/user/repos',{'name':name,'private':True,'description':'CineAgents: local multi-agent film recommendations and reproducible RecSys experiments','auto_init':False})
                status.update(url=repo['html_url'],created=True,private=repo['private'])
            if args.create and repo and not repo['private']:raise RuntimeError('Refusing to publish to an existing public repository')
            if args.create and repo:
                remote='https://github.com/'+user+'/'+name+'.git'
                current=subprocess.run(['git','-c','safe.directory=C:/KFU/DM/Task2','remote','get-url','origin'],capture_output=True,text=True)
                if current.returncode==0 and current.stdout.strip()!=remote: raise RuntimeError('Refusing to replace an existing remote')
                if current.returncode!=0: subprocess.run(['git','-c','safe.directory=C:/KFU/DM/Task2','remote','add','origin',remote],check=True)
        except urllib.error.HTTPError as exc:status['error']='GitHub HTTP '+str(exc.code)
        except urllib.error.URLError:status['error']='GitHub connection failed'
    Path('artifacts/repository_status.json').write_text(json.dumps(status,indent=2))
    print(json.dumps(status,indent=2))

if __name__=='__main__':main()
