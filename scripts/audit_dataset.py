from pathlib import Path
import json
from cineagents.data import load_dataset,temporal_split
from cineagents.recsys import Recommender

data=load_dataset();train,val,test=temporal_split(data.ratings);engine=Recommender(data,train)
rows=train[~engine.available[train[:,1]-1]]
result={'train_interactions_with_unavailable_release_metadata':len(rows),'items':sorted(set(map(int,rows[:,1]))),'positive_count':int((rows[:,2]>=4).sum())}
Path('artifacts/data_audit.json').write_text(json.dumps(result,indent=2));print(result)
