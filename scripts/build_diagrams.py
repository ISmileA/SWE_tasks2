"""Здесь мы строим семь диаграмм C4 и диаграмму последовательности, сохраняем SVG и PNG."""
from pathlib import Path
import json, textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

OUT=Path('docs/diagrams')


def wrapped(s,width=27):
    return '\n'.join('\n'.join(textwrap.wrap(line,width) or ['']) for line in s.split('\n'))


def render(key,title,nodes,edges,note=''):
    fig,ax=plt.subplots(figsize=(14,8)); ax.set_xlim(0,14); ax.set_ylim(0,8); ax.axis('off')
    ax.text(.3,7.65,title,fontsize=19,fontweight='bold',color='#183047')
    boxes={}
    for id,label,x,y in nodes:
        w,h=3.25,1.02; boxes[id]=(x,y,w,h)
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.06',facecolor='#eef3f6',edgecolor='#315b78',linewidth=1.4,zorder=3))
        ax.text(x+w/2,y+h/2,wrapped(label,29),ha='center',va='center',fontsize=10.5,zorder=4)
    for source,target,label in edges:
        x,y,w,h=boxes[source]; tx,ty,tw,th=boxes[target]
        a=(x+w/2,y+h/2); b=(tx+tw/2,ty+th/2)
        dx,dy=b[0]-a[0],b[1]-a[1]
        if abs(dx)>abs(dy)*1.7:
            p=(x+w if dx>0 else x,y+h/2); q=(tx if dx>0 else tx+tw,ty+th/2)
        else:
            p=(x+w/2,y+h if dy>0 else y); q=(tx+tw/2,ty if dy>0 else ty+th)
        routed=abs(dy)<.1 and (abs(dx)>w*1.5 or dx<0)
        if routed:
            p=(x+w/2,y);q=(tx+tw/2,ty)
        connection='arc3,rad='+str((.25 if dx>0 else -.25)) if routed else 'arc3,rad=0'
        ax.add_patch(FancyArrowPatch(p,q,arrowstyle='-|>',connectionstyle=connection,mutation_scale=12,color='#506574',linewidth=1,zorder=2))
        mx,my=(p[0]+q[0])/2,(p[1]+q[1])/2
        if routed:my-=abs(dx)*.125+.12
        ax.text(mx,my+.12,wrapped(label,22),ha='center',va='bottom',fontsize=8.5,bbox={'facecolor':'white','edgecolor':'none','pad':1},zorder=5)
    ax.text(.3,.15,note or 'C4 notation: boxes = named elements; arrows = directed relationships. Local educational deployment.',fontsize=8,color='#4a5967')
    fig.tight_layout(); fig.savefig(OUT/f'{key}.png',dpi=170); fig.savefig(OUT/f'{key}.svg'); plt.close(fig)


def deployment():
    fig,ax=plt.subplots(figsize=(14,8)); ax.set_xlim(0,14);ax.set_ylim(0,8);ax.axis('off')
    ax.text(.3,7.65,'07 / C4 Deployment - actual local topology',fontsize=19,fontweight='bold')
    for x,y,w,h,label,color in [(.25,.65,13.5,6.55,'Windows 11 / Ryzen 7 5800U / 16 GB RAM','#f7f8fa'),(3,.95,10.4,5.85,'WSL2 Ubuntu 22.04 / shared Linux kernel / 7.5 GiB RAM','#edf1f5'),(3.4,1.35,5.5,4.6,'Bubblewrap / PID + mount + network namespaces','#e2edf5')]:
        ax.add_patch(Rectangle((x,y),w,h,facecolor=color,edgecolor='#526c81',linewidth=1.4));ax.text(x+.15,y+h-.3,label,fontsize=11,fontweight='bold')
    entries=[(.6,3.1,2,1,'User / browser\n127.0.0.1:8000'),(3.8,4.05,4.7,1,'FastAPI + LangGraph\nUNIX socket API'),(3.8,2.65,4.7,.9,'SQLite + JSONL\nwriteable /app/runtime'),(3.8,1.6,4.7,.65,'Code / data / checkpoint: read-only'),(9.4,4.8,3.5,1,'HTTP proxy :8000\n+ inference UDS gateway'),(9.4,3.1,3.5,1,'Ollama :11435\n3 local CPU models'),(9.4,1.55,3.5,1,'Offline trainer / eval jobs\nversioned artifacts')]
    for x,y,w,h,label in entries:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.03',facecolor='white',edgecolor='#315b78'));ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=10)
    for p,q,label in [((2.65,3.6),(9.4,5.3),'HTTP through local proxy'),((9.4,5.05),(8.5,4.55),'API UDS'),((8.5,4.2),(9.4,4.85),'bounded inference UDS'),((11.1,4.8),(11.1,4.1),'local HTTP'),((11,2.55),(8.5,1.95),'model checkpoint')]:
        ax.add_patch(FancyArrowPatch(p,q,arrowstyle='-|>',mutation_scale=12,color='#536b7b'));ax.text((p[0]+q[0])/2,(p[1]+q[1])/2+.12,label,fontsize=8,ha='center',bbox={'facecolor':'white','edgecolor':'none','pad':1})
    ax.text(.3,.25,'Sandbox has no IP connectivity, host home or Windows mounts. Gateway/Ollama and the shared kernel remain trusted.',fontsize=9)
    fig.tight_layout();fig.savefig(OUT/'07-deployment.png',dpi=170);fig.savefig(OUT/'07-deployment.svg');plt.close(fig)


def sequence():
    fig,ax=plt.subplots(figsize=(15,10));ax.set_xlim(0,15);ax.set_ylim(0,11);ax.axis('off')
    ax.text(.2,10.7,'08 / Sequence - one request and bounded repair',fontsize=19,fontweight='bold')
    actors=['User','API / graph','Memory','Decision\nmodel','Planner\nQwen small/strong','Retrieval\ntool','Curator\nQwen strong','Validator\nGemma']
    xs=[.8+i*1.9 for i in range(len(actors))]
    for x,label in zip(xs,actors):
        ax.add_patch(Rectangle((x-.78,9.65),1.56,.7,facecolor='#eef3f6',edgecolor='#315b78'));ax.text(x,10,label,ha='center',va='center',fontsize=10.5);ax.plot([x,x],[.7,9.65],linestyle='--',color='#aab7c0',linewidth=.8)
    steps=[(0,1,'1. POST /agent'),(1,2,'2. Read user preferences + recent episodes'),(2,1,'3. Scoped memory / TTL checked'),(1,3,'4. Typed route + confidence'),(3,1,'5. Escalate on low confidence'),(1,4,'6. Request typed plan via inference UDS'),(4,1,'7. Method + genre'),(1,5,'8. Execute allowlisted recommendation tool'),(5,1,'9. Eligible unseen candidates'),(1,6,'10. Select k supplied IDs'),(6,1,'11. Selection JSON'),(1,7,'12. Independent check via inference UDS'),(7,1,'13. Verdict + deterministic grounding checks'),(1,6,'14. If rejected: repair once; repeat validation'),(1,2,'15. On success: save episode with TTL'),(1,0,'16. Evidence-based result or explicit rejection')]
    for j,(a,b,label) in enumerate(steps):
        y=9.25-j*.5;p=(xs[a],y);q=(xs[b],y)
        ax.add_patch(FancyArrowPatch(p,q,arrowstyle='-|>',mutation_scale=11,color='#315b78',linewidth=1))
        ax.text((p[0]+q[0])/2,y+.07,wrapped(label,52),ha='center',fontsize=10,bbox={'facecolor':'white','edgecolor':'none','pad':1})
    ax.text(.2,.3,'All stages emit spans with trace_id. Unsafe routes terminate before tools; unavailable inference is an error, never a synthetic answer.',fontsize=9)
    fig.tight_layout();fig.savefig(OUT/'08-sequence.png',dpi=170);fig.savefig(OUT/'08-sequence.svg');plt.close(fig)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    views=[
      ('01-landscape','01 / C4 System Landscape',[
        ('u','Student / viewer\n[Person]',.4,5.7),('c','CineAgents\n[Software system]',5.3,5.7),('o','Local Ollama\n[Software system]',10.2,5.7),('d','Developer / evaluator\n[Person]',.4,2),('g','GroupLens / MovieLens\n[External system]',5.3,2),('r','Git repository + report\n[External system]',10.2,2)],
       [('u','c','Requests recommendations'),('c','o','Local structured inference'),('g','c','Versioned research data'),('d','c','Runs experiments'),('d','r','Versions evidence'),('c','r','Exports artifacts')]),
      ('02-context','02 / C4 System Context',[
        ('u','Viewer\n[Person]',.4,4),('s','CineAgents\n[System of interest]',5.3,4),('m','Local model serving\n[External system]',10.2,5.7),('g','GroupLens dataset\n[External system]',10.2,2),('e','Authors / examiner\n[Person]',.4,1.5)],
       [('u','s','Film request + preferences'),('s','m','Grounded JSON decisions'),('g','s','Historical ratings + metadata'),('e','s','Tests, traces, PDF evidence')]),
      ('03-containers','03 / C4 Containers (logical processes and stores)',[
        ('a','Local HTTP proxy\n[Python process]',.4,5.7),('b','API + LangGraph\n[Sandbox process]',5.3,5.7),('l','Inference gateway + Ollama\n[Linux processes]',10.2,5.7),('d','MovieLens + checkpoint\n[Read-only files]',.4,2),('m','User memory\n[SQLite store]',5.3,2),('o','Events / metrics / alerts\n[JSONL + API]',10.2,2)],
       [('a','b','HTTP over UNIX socket'),('b','l','Bounded UNIX socket'),('d','b','Train-only model + catalogue'),('b','m','Scoped TTL reads/writes'),('b','o','Spans and decisions')]),
      ('04-components','04 / C4 Components inside API + LangGraph',[
        ('g','DecisionModel + ModelRouter\n[Routing component]',.4,5.7),('p','Planner\n[Agent component]',5.3,5.7),('t','Recommender tool\n[Retrieval component]',10.2,5.7),('m','Memory adapter\n[Persistence component]',.4,2),('c','Curator\n[Agent component]',5.3,2),('v','Validator + final checks\n[Verification component]',10.2,2)],
       [('g','p','Budget + model'),('p','t','Typed retrieval plan'),('t','c','Grounded candidates'),('c','v','k selected IDs'),('v','m','Accepted episode'),('m','p','Preferences + episodes')]),
      ('05-code','05 / C4 Code view - implemented class relationships',[
        ('a','AgentSystem\nrun / graph nodes',5.3,5.7),('r','ModelRouter\nmodel(role, complexity)',.4,5.7),('l','OllamaInference\ngenerate(JSON schema)',10.2,5.7),('m','Memory\npreferences / episodes',.4,2),('e','Recommender + TwoTower\nrecommend / scores',5.3,2),('o','Observer\nspan / event / alert',10.2,2)],
       [('r','a','Provides model ID'),('a','l','Calls typed inference'),('a','m','Reads/writes scoped data'),('a','e','Calls retrieval'),('a','o','Emits correlated events')]),
      ('06-dynamic','06 / C4 Dynamic - successful request and repair path',[
        ('r','1. Route decision\nconfidence + budget',.4,5.7),('p','2. Planner\nmethod + genre',5.3,5.7),('t','3. Retrieval\nfilter seen + availability',10.2,5.7),('f','6. Finalize\nstore evidence + result',.4,2),('c','4. Curator\nselect k IDs',5.3,2),('v','5. Validator\nGemma + hard checks',10.2,2)],
       [('r','p','1. Route'),('p','t','2. Execute plan'),('t','c','3. Candidate evidence'),('c','v','4. Audit'),('v','f','5. If accepted'),('v','c','Reject: repair at most once')])
    ]
    for key,title,nodes,edges in views: render(key,title,nodes,edges)
    deployment();sequence()
    (OUT/'definitions.json').write_text(json.dumps([{'file':k,'title':t,'nodes':n,'edges':e} for k,t,n,e in views],indent=2))
    (OUT/'README.md').write_text('# Диаграммы\n\n01 Landscape, 02 Context, 03 Container, 04 Component, 05 Code, 06 Dynamic, 07 Deployment, 08 Sequence.\n\nPNG для отчёта, SVG для масштабирования. Исходники: scripts/build_diagrams.py и definitions.json. Container в C4 означает приложение/хранилище, а не обязательно Docker-контейнер.\n',encoding='utf-8')

if __name__=='__main__': main()
