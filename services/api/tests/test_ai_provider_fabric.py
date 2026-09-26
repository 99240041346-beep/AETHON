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


class CaptureProvider(AIProvider):
    def __init__(self):
        self.seen_prompt = None
        self.seen_user_text = None

    def info(self):
        return ProviderInfo("capture", "fake", "test-model", True, ("chat",))

    def generate(self, prompt, user_text=None):
        self.seen_prompt = prompt
        self.seen_user_text = user_text
        return ProviderResult("capture", "test-model", "context-aware", True, {})


def test_provider_receives_full_context_prompt():
    provider = CaptureProvider()
    fabric = AIProviderFabric([provider])
    result = fabric.generate("history: user asked about Python\nUser: what about decorators?", user_text="what about decorators?")
    assert result.text == "context-aware"
    assert "history: user asked about Python" in provider.seen_prompt
    assert provider.seen_user_text == "what about decorators?"
