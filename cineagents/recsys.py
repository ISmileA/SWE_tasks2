import numpy as np
from scipy.sparse import csr_matrix


METHODS=('content','item_cf','popularity','bayesian','hybrid','two_tower')


class Recommender:
    def __init__(self, dataset, train):
        self.dataset, self.train = dataset, train
        self.n=dataset.n_items
        self.cutoff=int(train[:,3].max())
        self.available=np.ones(self.n,dtype=bool) if dataset.released is None else dataset.released<=self.cutoff
        self.seen={int(u):set(map(int,train[train[:,0]==u,1])) for u in np.unique(train[:,0])}
        # В MovieLens часть оценок не согласуется с датами выхода фильмов.
        # Мы сохраняем их в истории просмотров, чтобы исключать повторы,
        # но не включаем недоступные признаки в обучение профиля.
        self.positive=train[(train[:,2]>=4)&self.available[train[:,1]-1]]
        ui=csr_matrix((np.ones(len(self.positive)),(self.positive[:,0]-1,self.positive[:,1]-1)),shape=(dataset.n_users,self.n),dtype=np.float32)
        self.ui=ui
        self.popularity=np.asarray(ui.sum(axis=0)).ravel()
        cnt=np.bincount(train[:,1]-1,minlength=self.n)
        sums=np.bincount(train[:,1]-1,weights=train[:,2],minlength=self.n)
        self.bayesian=(sums+20*train[:,2].mean())/(cnt+20)
        f=dataset.features.copy()
        self.features=f/np.maximum(np.linalg.norm(f,axis=1,keepdims=True),1e-12)
        co=(ui.T@ui).toarray()
        denominator=np.sqrt(np.outer(self.popularity,self.popularity))
        self.similarity=np.divide(co,denominator,out=np.zeros_like(co),where=denominator>0)*(co/(co+10))
        np.fill_diagonal(self.similarity,0)
        self.neural=None

    def scores(self,user_id,method):
        if method not in METHODS: raise ValueError(f'Unknown method: {method}')
        known=user_id in self.seen
        if method=='popularity': return self.popularity.copy()
        if method=='bayesian': return self.bayesian.copy()
        if not known: return self.popularity.copy()
        history=self.positive[self.positive[:,0]==user_id]
        if not len(history): return self.popularity.copy()
        if method=='content':
            profile=(self.features[history[:,1]-1]*(history[:,2]-3)[:,None]).sum(axis=0)
            norm=np.linalg.norm(profile)
            return self.features@(profile/max(norm,1e-12))
        if method=='item_cf': return np.asarray(self.ui.getrow(user_id-1)@self.similarity).ravel()
        if method=='two_tower':
            if self.neural is None: raise RuntimeError('Train/load Two-Tower first')
            return self.neural.scores(user_id)
        # Мы объединяем позиции в списках: сырые баллы этих методов несопоставимы.
        a,b=self.scores(user_id,'content'),self.scores(user_id,'item_cf')
        out=np.zeros(self.n)
        for score in (a,b):
            order=np.lexsort((np.arange(self.n),-score))
            out[order]+=1/(60+np.arange(self.n)+1)
        return out

    def recommend(self,user_id,method='hybrid',k=10,genre=None):
        if not isinstance(user_id,int) or user_id<1: raise ValueError('user_id must be positive')
        if not isinstance(k,int) or not 1<=k<=100: raise ValueError('k must be 1..100')
        if genre is not None and genre not in self.dataset.genres: raise ValueError('Unknown genre')
        score=self.scores(user_id,method)
        has_positive=bool(np.any(self.positive[:,0]==user_id))
        effective=method if method in ('popularity','bayesian') or has_positive else 'popularity'
        allowed=self.available.copy()
        if genre is not None: allowed &= self.dataset.features[:,self.dataset.genres.index(genre)]>0
        for item in self.seen.get(user_id,set()): allowed[item-1]=False
        ids=np.where(allowed & np.isfinite(score))[0]
        ids=ids[np.lexsort((ids,-score[ids]))][:k]
        return [{'movie_id':int(i+1),'title':self.dataset.titles[int(i+1)],'genres':[g for g,x in zip(self.dataset.genres,self.dataset.features[i]) if x], 'score':float(score[i]),'method':effective,'requested_method':method,'fallback_reason':'no_positive_train_history' if effective!=method else None,'source':'MovieLens 100K'} for i in ids]
