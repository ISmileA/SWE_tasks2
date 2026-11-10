"""Здесь мы обучаем и сравниваем методы. Запуск: python -m scripts.train_eval."""
from pathlib import Path
import argparse, csv, json, time, platform, hashlib
import numpy as np
import psutil
from cineagents.data import load_dataset, temporal_split
from cineagents.recsys import Recommender
from cineagents.twotower import TwoTower
from cineagents.evaluation import evaluate


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--epochs',type=int,default=20)
    args=parser.parse_args()
    root=Path('artifacts'); root.mkdir(exist_ok=True)
    start=time.time(); dataset=load_dataset(); train,val,test=temporal_split(dataset.ratings)
    engine=Recommender(dataset,train)
    manifest={'split':'global timestamp 70/15/15; ties kept together','threshold':4,'k':10,'seed':42,
              'train':len(train),'validation':len(val),'test':len(test),'users':dataset.n_users,'items':dataset.n_items,
              'available_at_train_cutoff':int(engine.available.sum()),'train_max_timestamp':int(train[:,3].max()),
              'excluded_train_positive_release_conflicts':int(((train[:,2]>=4)&~engine.available[train[:,1]-1]).sum()),
              'validation_min_timestamp':int(val[:,3].min()),'validation_max_timestamp':int(val[:,3].max()),'test_min_timestamp':int(test[:,3].min()),
              'platform':platform.platform(),'cpu_count':psutil.cpu_count(),'memory_total':psutil.virtual_memory().total,
              'dataset_sha256':hashlib.sha256(Path('data/ml-100k/u.data').read_bytes()).hexdigest()}
    (root/'experiment.json').write_text(json.dumps(manifest,indent=2))
    methods=['popularity','bayesian','content','item_cf','hybrid']
    validation={method:evaluate(engine,val,method)[0] for method in methods}
    print('BASELINE_VALIDATION',validation,flush=True)
    # Мы сравниваем две скорости обучения только по проверочной выборке, без тестовой.
    trials=[]
    for lr in [.001,.003]:
        neural=TwoTower(engine,seed=42).fit(epochs=args.epochs,lr=lr,validation=val)
        vm=evaluate(engine,val,'two_tower')[0]
        file=root/f'two_tower_lr{lr}.pt'; neural.save(file)
        trials.append({'lr':lr,'best_epoch':neural.best_epoch,'validation':vm,'checkpoint':str(file),'history':neural.log})
    winner=max(trials,key=lambda r:r['validation']['ndcg'])
    engine.neural=TwoTower.load(engine,winner['checkpoint']); engine.neural.save(root/'two_tower.pt')
    validation['two_tower']=winner['validation']; methods.append('two_tower')
    results={}; raw=[]
    for method in methods:
        metrics,rows=evaluate(engine,test,method)
        results[method]=metrics
        raw.extend(dict(method=method,**r) for r in rows)
        print('TEST',method,metrics,flush=True)
    best_method=max(validation,key=lambda m:validation[m]['ndcg'])
    (root/'recsys_results.json').write_text(json.dumps({'validation':validation,'test':results,'selected_serving_method':best_method,'neural_selection':winner['lr'],'trials':trials,'elapsed_seconds':time.time()-start},indent=2))
    with (root/'recsys_per_user.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(raw[0])); writer.writeheader(); writer.writerows(raw)
    # Мы сравниваем разницу на одинаковых пользователях с помощью парного bootstrap.
    baseline='popularity'; rng=np.random.default_rng(42); comparisons={}
    for method in methods:
        a={r['user_id']:r['ndcg'] for r in raw if r['method']==method}
        b={r['user_id']:r['ndcg'] for r in raw if r['method']==baseline}
        diffs=np.array([a[u]-b[u] for u in sorted(a.keys()&b.keys())])
        means=np.array([rng.choice(diffs,len(diffs),replace=True).mean() for _ in range(2000)])
        comparisons[method]={'mean_ndcg_delta_vs_popularity':float(diffs.mean()),'paired_bootstrap_95_ci':list(map(float,np.quantile(means,[.025,.975])))}
    (root/'bootstrap.json').write_text(json.dumps(comparisons,indent=2))
    print('DONE',best_method,flush=True)

if __name__=='__main__': main()
