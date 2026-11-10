import time
import numpy as np


def ranking_metrics(prediction,truth,k=10):
    prediction=list(prediction[:k]); truth=set(truth)
    if k<=0 or not truth: raise ValueError('Need positive k and nonempty ground truth')
    if len(set(prediction))!=len(prediction): raise ValueError('Duplicate recommendations')
    relevance=np.array([int(x in truth) for x in prediction])
    discounts=1/np.log2(np.arange(len(prediction))+2)
    dcg=float((relevance*discounts).sum())
    ideal=float((1/np.log2(np.arange(min(len(truth),k))+2)).sum())
    positions=np.flatnonzero(relevance)
    return {'precision':float(relevance.sum()/k),'recall':float(relevance.sum()/len(truth)),
            'ndcg':dcg/ideal,'hit_rate':float(bool(relevance.any())),
            'mrr':float(1/(positions[0]+1)) if len(positions) else 0.0}


def evaluate(engine,holdout,method,k=10):
    """Мы оцениваем весь доступный каталог для пользователей с положительными тестовыми оценками."""
    positive=holdout[holdout[:,2]>=4]
    per_user=[]; recommended=set(); latencies=[]; cold_users=0; excluded=0; eligible_total=0
    counts=engine.popularity
    for user in sorted(map(int,np.unique(positive[:,0]))):
        raw=set(map(int,positive[positive[:,0]==user,1]))-engine.seen.get(user,set())
        truth={i for i in raw if engine.available[i-1]}
        excluded+=len(raw-truth); eligible_total+=len(truth)
        if not truth: continue
        start=time.perf_counter()
        rows=engine.recommend(user,method,k)
        latencies.append((time.perf_counter()-start)*1000)
        ids=[r['movie_id'] for r in rows]
        m=ranking_metrics(ids,truth,k)
        m['user_id']=user
        cold=user not in engine.seen
        m['cold_user']=cold; cold_users+=cold
        idx=np.asarray(ids,dtype=int)-1
        if len(idx)>1:
            sims=engine.features[idx]@engine.features[idx].T
            m['diversity']=float(1-sims[np.triu_indices(len(idx),1)].mean())
        else: m['diversity']=0.0
        prob=(counts[idx]+1)/(counts.sum()+len(counts))
        m['novelty']=float(-np.log2(prob).mean()) if len(idx) else 0
        per_user.append(m); recommended.update(ids)
    metrics={name:float(np.mean([row[name] for row in per_user])) for name in ['precision','recall','ndcg','hit_rate','mrr','diversity','novelty']} if per_user else {}
    metrics.update({'users':len(per_user),'cold_users':cold_users,'coverage':len(recommended)/max(1,int(engine.available.sum())),
                    'latency_ms_p50':float(np.percentile(latencies,50)) if latencies else 0,'latency_ms_p95':float(np.percentile(latencies,95)) if latencies else 0,
                    'excluded_unavailable_relevant':excluded,'eligible_relevant':eligible_total})
    for cohort,cold in [('warm',False),('cold',True)]:
        subset=[row for row in per_user if row['cold_user']==cold]
        metrics[cohort+'_users']=len(subset)
        metrics[cohort+'_ndcg']=float(np.mean([r['ndcg'] for r in subset])) if subset else None
    return metrics,per_user
