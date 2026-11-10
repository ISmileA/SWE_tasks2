import math
import numpy as np
import pytest
from cineagents.evaluation import ranking_metrics
from cineagents.twotower import sample_negatives


def test_metrics_match_hand_computed_ranking():
    # Мы задаём попадания на первом и третьем местах; один подходящий фильм пропущен.
    m=ranking_metrics([2,7,5],{2,5,9},3)
    assert m['precision']==pytest.approx(2/3)
    assert m['recall']==pytest.approx(2/3)
    assert m['ndcg']==pytest.approx(1.5/(1+1/math.log2(3)+.5))
    assert m['mrr']==1
    assert m['hit_rate']==1


def test_duplicate_recommendations_cannot_inflate_metrics():
    with pytest.raises(ValueError): ranking_metrics([2,2],{2},2)


def test_negative_sampling_never_uses_observed_items():
    rng=np.random.default_rng(42)
    seen={1:{1,2,3},2:{2,3,4}}
    negatives=sample_negatives(np.array([1,2]*50),seen,4,rng)
    assert set(negatives[::2])=={4}
    assert set(negatives[1::2])=={1}
    with pytest.raises(ValueError): sample_negatives(np.array([1]),{1:{1,2}},2,rng)


def test_negative_sampling_excludes_unavailable_future_items():
    values=sample_negatives(np.array([1]*100),{1:{1}},4,np.random.default_rng(42),allowed_items=np.array([1,2]))
    assert set(values)=={2}
