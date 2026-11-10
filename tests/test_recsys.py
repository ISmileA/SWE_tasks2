"""Здесь мы проверяем утечки будущих данных, повторы просмотренных фильмов и нового пользователя."""
import numpy as np
import pytest
from cineagents.data import Dataset, temporal_split
from cineagents.recsys import Recommender


@pytest.fixture
def fixture():
    # В тестовых данных мы задаём: пользователь, фильм, оценка, время.
    ratings = np.array([[1,1,5,1],[1,2,4,2],[2,1,5,3],[2,3,4,4],[3,4,5,5]])
    return Dataset(ratings, {1:'One',2:'Two',3:'Three',4:'Four'},
                   np.array([[1,0],[1,0],[0,1],[0,1]],dtype=float), ['Comedy','Drama'])


def test_global_time_split_keeps_equal_timestamps_together():
    ratings = np.array([[1,1,5,1],[2,2,5,2],[3,3,5,2],[4,4,5,3],[5,4,5,4]])
    train, val, test = temporal_split(ratings, .5, .25)
    assert train[:,3].max() < val[:,3].min()
    assert val[:,3].max() < test[:,3].min()
    assert len(train)+len(val)+len(test)==5


@pytest.mark.parametrize('method',['content','item_cf','popularity','bayesian'])
def test_all_methods_exclude_seen_and_respect_genre(fixture, method):
    engine=Recommender(fixture, fixture.ratings)
    result=engine.recommend(1,method,10,genre='Drama')
    assert {r['movie_id'] for r in result}=={3,4}
    assert all(r['source']=='MovieLens 100K' for r in result)


def test_cold_user_gets_train_only_popularity(fixture):
    engine=Recommender(fixture, fixture.ratings[:4])
    assert engine.recommend(999,'popularity',1)[0]['movie_id']==1
    assert engine.recommend(999,'content',1)[0]['movie_id']==1
    assert engine.recommend(999,'popularity',10)[-1]['movie_id']==4


def test_invalid_inputs_are_not_silently_ignored(fixture):
    engine=Recommender(fixture, fixture.ratings)
    with pytest.raises(ValueError): engine.recommend(1,'shell',2)
    with pytest.raises(ValueError): engine.recommend(1,'content',2,genre='injected')
    with pytest.raises(ValueError): engine.recommend(1,'content',0)


def test_cold_start_reports_actual_baseline_instead_of_neural_claim(fixture):
    engine=Recommender(fixture,fixture.ratings)
    row=engine.recommend(999,'two_tower',1)[0]
    assert row['method']=='popularity'
    assert row['requested_method']=='two_tower'


def test_future_or_unknown_release_metadata_does_not_enter_positive_profiles(fixture):
    fixture.released=np.array([0,0,100,0],dtype=float)
    engine=Recommender(fixture,fixture.ratings)
    assert 3 not in set(engine.positive[:,1])
    assert 3 in engine.seen[2]  # observed history is still excluded from repeat recommendations
