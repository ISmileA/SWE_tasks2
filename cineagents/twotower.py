"""В Two-Tower мы используем две отдельные сети и обучаем их сравнивать пары фильмов по BPR."""
import copy
import numpy as np
import torch
from torch import nn


def sample_negatives(users,seen,n_items,rng,allowed_items=None):
    pool=np.arange(1,n_items+1) if allowed_items is None else np.asarray(allowed_items,dtype=int)
    if not len(pool) or len(np.unique(pool))!=len(pool) or np.any((pool<1)|(pool>n_items)): raise ValueError('Invalid negative candidate pool')
    out=rng.choice(pool,size=len(users))
    # Для отбора отрицательных примеров мы используем только историю из обучения.
    eligible=set(map(int,pool))
    if any(eligible.issubset(seen.get(int(u),set())) for u in np.unique(users)):
        raise ValueError('No unseen negative for a user')
    invalid=np.array([int(i) in seen.get(int(u),set()) for u,i in zip(users,out)])
    while invalid.any():
        out[invalid]=rng.choice(pool,size=int(invalid.sum()))
        invalid=np.array([int(i) in seen.get(int(u),set()) for u,i in zip(users,out)])
    return out


class Towers(nn.Module):
    def __init__(self,n_users,n_items,n_genres,dim=32):
        super().__init__()
        self.user_embedding=nn.Embedding(n_users,dim)
        self.item_embedding=nn.Embedding(n_items,dim)
        self.user_tower=nn.Sequential(nn.Linear(dim+n_genres,64),nn.ReLU(),nn.Linear(64,dim))
        self.item_tower=nn.Sequential(nn.Linear(dim+n_genres,64),nn.ReLU(),nn.Linear(64,dim))
        nn.init.normal_(self.user_embedding.weight,std=.05)
        nn.init.normal_(self.item_embedding.weight,std=.05)

    def user(self,ids,profiles): return self.user_tower(torch.cat([self.user_embedding(ids),profiles[ids]],dim=-1))
    def item(self,ids,features): return self.item_tower(torch.cat([self.item_embedding(ids),features[ids]],dim=-1))


class TwoTower:
    def __init__(self,engine,dim=32,seed=42):
        torch.set_num_threads(4)
        torch.manual_seed(seed); self.rng=np.random.default_rng(seed)
        self.engine=engine; self.seed=seed; self.dim=dim
        self.model=Towers(engine.dataset.n_users,engine.n,len(engine.dataset.genres),dim)
        self.features=torch.tensor(engine.dataset.features,dtype=torch.float32)
        profiles=np.asarray(engine.ui@engine.features)
        profiles=profiles/np.maximum(np.linalg.norm(profiles,axis=1,keepdims=True),1e-12)
        self.profiles=torch.tensor(profiles,dtype=torch.float32)
        self.log=[]; self.embeddings=None

    def fit(self,epochs=20,lr=.003,batch_size=1024,validation=None):
        from cineagents.evaluation import evaluate
        opt=torch.optim.Adam(self.model.parameters(),lr=lr,weight_decay=1e-5)
        pairs=self.engine.positive[:,:2]
        best=-1; best_state=None
        for epoch in range(1,epochs+1):
            self.model.train(); losses=[]
            order=self.rng.permutation(len(pairs))
            negatives=sample_negatives(pairs[:,0],self.engine.seen,self.engine.n,self.rng,allowed_items=np.flatnonzero(self.engine.available)+1)
            for start in range(0,len(order),batch_size):
                ix=order[start:start+batch_size]
                u=torch.tensor(pairs[ix,0]-1,dtype=torch.long)
                p=torch.tensor(pairs[ix,1]-1,dtype=torch.long)
                n=torch.tensor(negatives[ix]-1,dtype=torch.long)
                uv=self.model.user(u,self.profiles)
                pv=self.model.item(p,self.features); nv=self.model.item(n,self.features)
                margin=(uv*(pv-nv)).sum(dim=1)
                loss=nn.functional.softplus(-margin).mean()
                opt.zero_grad(); loss.backward(); opt.step(); losses.append(float(loss.detach()))
            self.refresh()
            self.engine.neural=self
            metric=evaluate(self.engine,validation,'two_tower')[0]['ndcg'] if validation is not None else -float(np.mean(losses))
            self.log.append({'epoch':epoch,'bpr_loss':float(np.mean(losses)),'validation_ndcg':metric if validation is not None else None})
            print(self.log[-1],flush=True)
            if metric>best or best_state is None:
                best=metric; best_state=copy.deepcopy(self.model.state_dict()); self.best_epoch=epoch
        self.model.load_state_dict(best_state); self.refresh()
        return self

    def refresh(self):
        self.model.eval()
        with torch.no_grad():
            users=self.model.user(torch.arange(self.engine.dataset.n_users),self.profiles)
            items=self.model.item(torch.arange(self.engine.n),self.features)
            self.embeddings=(users.numpy(),items.numpy())

    def scores(self,user_id):
        u,i=self.embeddings
        return i@u[user_id-1]

    def save(self,path):
        torch.save({'state':self.model.state_dict(),'seed':self.seed,'dim':self.dim,'best_epoch':self.best_epoch,'log':self.log},path)

    @classmethod
    def load(cls,engine,path):
        data=torch.load(path,map_location='cpu',weights_only=True)
        obj=cls(engine,data['dim'],data['seed']); obj.model.load_state_dict(data['state'])
        obj.best_epoch=data['best_epoch']; obj.log=data['log']; obj.refresh()
        return obj
