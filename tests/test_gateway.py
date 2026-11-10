import pytest
from cineagents.gateway import validate_request


def test_gateway_restricts_models_context_and_paths():
    valid={'model':'qwen3:0.6b','options':{'num_ctx':4096,'num_predict':256}}
    assert validate_request('/api/chat',valid) is None
    for payload in [{'model':'arbitrary-cloud-model'}, {'model':'qwen3:0.6b','options':{'num_ctx':1000000}}, {'model':'qwen3:0.6b','options':{'num_predict':-1}}]:
        with pytest.raises(ValueError): validate_request('/api/chat',payload)
    with pytest.raises(ValueError): validate_request('/api/pull',valid)


@pytest.mark.parametrize('extra',[{'keep_alive':-1},{'options':{'num_batch':1000000}},{'options':{'num_thread':-1}},{'stream':True},{'options':{'num_ctx':True}}])
def test_gateway_rejects_resource_limit_bypasses(extra):
    with pytest.raises(ValueError): validate_request('/api/chat',{'model':'qwen3:0.6b',**extra})


def test_gateway_materializes_limits_in_forwarded_body():
    body={'model':'qwen3:0.6b'}
    validate_request('/api/chat',body)
    assert body['options']['num_ctx']==4096
    assert body['options']['num_predict']==256
    assert body['options']['num_thread']==6
    assert body['keep_alive']=='2m' and body['stream'] is False
