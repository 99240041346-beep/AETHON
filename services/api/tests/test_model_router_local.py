from aethon.model_router import LocalIntelligenceProvider, OpenAICompatibleProvider


def test_local_intelligence_answers_common_questions():
    provider = LocalIntelligenceProvider()
    answer = provider.generate("ignored", user_text="What is B.Tech?")
    assert "Bachelor of Technology" in answer
    assert "undergraduate" in answer


def test_local_intelligence_does_not_claim_unavailable_general_model():
    provider = LocalIntelligenceProvider()
    answer = provider.generate("ignored", user_text="Explain a completely unknown topic")
    assert "remote language model" in answer
    assert "unrestricted answer" in answer


def test_compatible_provider_uses_explicit_user_text(monkeypatch):
    provider = OpenAICompatibleProvider("https://example.test/v1", "demo", "secret")
    captured = {}

    class Response:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}]}

    def fake_post(url, **kwargs):
        captured["payload"] = kwargs["json"]
        return Response()

    monkeypatch.setattr("aethon.model_router.httpx.post", fake_post)
    assert provider.generate("internal context", user_text="actual question") == "ok"
    assert captured["payload"]["messages"][1]["content"] == "actual question"


def test_local_intelligence_handles_greeting_and_small_talk():
    provider = LocalIntelligenceProvider()
    assert provider.generate("", user_text="Hello AETHON") == "Hello! I'm AETHON. How can I help you today?"
    assert "You're welcome" in provider.generate("", user_text="Thank you")
    assert "Goodbye" in provider.generate("", user_text="bye")


def test_local_intelligence_covers_web_stack_basics():
    provider = LocalIntelligenceProvider()
    assert "markup language" in provider.generate("", user_text="What is HTML?")
    assert "JavaScript" in provider.generate("", user_text="javascript")
    assert "PostgreSQL" in provider.generate("", user_text="what is postgresql?")
