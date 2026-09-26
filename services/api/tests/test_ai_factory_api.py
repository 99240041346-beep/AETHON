from app.ai_factory_api import _factory
from aethon.ai_factory import FactoryStage

def test_factory_is_owner_scoped():
    a = _factory("owner-a")
    b = _factory("owner-b")
    assert a is not b
    x = a.specify(__import__("aethon.ai_factory", fromlist=["AIAgentSpec"]).AIAgentSpec(name="X", goal="test"))
    assert x.stage is FactoryStage.SPECIFIED
    assert not b.agents
