from cineagents.decision import DecisionModel


def test_decision_returns_normalized_probabilities_and_escalates_uncertainty():
    model=DecisionModel(threshold=.9999)
    result=model.decide('неизвестный запрос xyz')
    assert abs(sum(result['probabilities'].values())-1)<1e-9
    assert result['route']=='complex' and result['escalated']
    assert result['latency_ms']>=0
