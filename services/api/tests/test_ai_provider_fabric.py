from aethon.ai_provider_fabric import AIProviderFabric, ProviderInfo, ProviderResult, AIProvider


class FakeProvider(AIProvider):
    def __init__(self, provider_id: str, value: str):
        self.provider_id = provider_id
        self.value = value

    def info(self):
        return ProviderInfo(self.provider_id, "fake", "test-model", True, ("chat", "code"))

    def generate(self, prompt, user_text=None):
        return ProviderResult(self.provider_id, "test-model", self.value, True, {})


def test_lists_configured_providers():
    fabric = AIProviderFabric([FakeProvider("one", "ok"), FakeProvider("two", "ok")])
    assert [item.id for item in fabric.list()] == ["one", "two"]
    assert fabric.capabilities()["one"] == ["chat", "code"]


def test_explicit_provider_is_used():
    fabric = AIProviderFabric([FakeProvider("one", "one"), FakeProvider("two", "two")])
    result = fabric.generate("hello", provider="two")
    assert result.provider == "two"
    assert result.text == "two"
