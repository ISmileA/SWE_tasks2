from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
import numpy as np


@dataclass
class Dataset:
    ratings: np.ndarray
    titles: dict[int, str]
    features: np.ndarray
    genres: list[str]
    released: np.ndarray | None = None

    @property
    def n_items(self): return len(self.titles)

    @property
    def n_users(self): return int(self.ratings[:,0].max())


def load_dataset(path='data/ml-100k') -> Dataset:
    path=Path(path)
    ratings=np.loadtxt(path/'u.data',dtype=np.int64)
    genres=[line.split('|')[0] for line in (path/'u.genre').read_text().splitlines() if line]
    titles, features, released = {}, [], []
    for line in (path/'u.item').read_text(encoding='latin-1').splitlines():
        cols=line.split('|')
        titles[int(cols[0])]=cols[1]
        features.append([int(x) for x in cols[5:]])
        try: stamp=datetime.strptime(cols[2],'%d-%b-%Y').replace(tzinfo=timezone.utc).timestamp()
        except ValueError: stamp=float('inf')  # unknown release: conservative exclusion
        released.append(stamp)
    if list(titles)!=list(range(1,len(titles)+1)):
        raise ValueError('Expected contiguous MovieLens item IDs')
    return Dataset(ratings,titles,np.asarray(features,dtype=np.float32),genres,np.asarray(released))


def temporal_split(ratings, train_fraction=.7, val_fraction=.15):
    """Мы разделяем оценки по времени и оставляем одинаковые метки времени в одной выборке."""
    if not (0 < train_fraction < 1 and 0 < val_fraction < 1-train_fraction):
        raise ValueError('Invalid split fractions')
    stamps=np.sort(np.unique(ratings[:,3]))
    if len(stamps)<3: raise ValueError('Need at least three distinct timestamps')
    sorted_time=np.sort(ratings[:,3])
    cut1=sorted_time[min(len(ratings)-1,int(len(ratings)*train_fraction))]
    cut2=sorted_time[min(len(ratings)-1,int(len(ratings)*(train_fraction+val_fraction)))]
    result=(ratings[ratings[:,3]<cut1],ratings[(ratings[:,3]>=cut1)&(ratings[:,3]<cut2)],ratings[ratings[:,3]>=cut2])
    if any(len(x)==0 for x in result): raise ValueError('Temporal split produced an empty partition')
    return result
