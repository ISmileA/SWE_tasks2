"""Для выбора маршрута мы используем небольшой Jev-like классификатор. Защиту ему не доверяем."""
from pathlib import Path
import json, time
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV


class DecisionModel:
    def __init__(self,threshold=.75):
        self.threshold=threshold
        base=Path(__file__).resolve().parent.parent
        data=json.loads((base/'data'/'routing_examples.json').read_text(encoding='utf-8'))['train']
        texts=[t for items in data.values() for t in items]
        labels=[label for label,items in data.items() for _ in items]
        classifier=make_pipeline(TfidfVectorizer(analyzer='char_wb',ngram_range=(2,5),sublinear_tf=True),LogisticRegression(C=6,max_iter=1000,random_state=42))
        self.model=CalibratedClassifierCV(classifier,method='sigmoid',cv=3)
        self.model.fit(texts,labels)

    def decide(self,text):
        start=time.perf_counter()
        probabilities=self.model.predict_proba([text])[0]
        idx=int(np.argmax(probabilities)); label=str(self.model.classes_[idx]); confidence=float(probabilities[idx])
        # При низкой уверенности мы выбираем более сильную модель.
        # Ограничения инструментов действуют, даже если классификатор пропустит опасный запрос.
        route=label if confidence>=self.threshold else 'complex'
        return {'route':route,'predicted_label':label,'confidence':confidence,'probabilities':{str(k):float(v) for k,v in zip(self.model.classes_,probabilities)},
                'escalated':confidence<self.threshold,'latency_ms':(time.perf_counter()-start)*1000}
