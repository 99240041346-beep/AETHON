import pytest

from aethon.model_routing import IntelligentModelRouter, ModelProfile, TaskComplexity


def models():
    return [
        ModelProfile("fast", frozenset({"general"}), 0.01, 100, provider="p1"),
        ModelProfile("reasoner", frozenset({"general", "reasoning"}), 0.05, 300, provider="p2"),
        ModelProfile("researcher", frozenset({"general", "reasoning", "research"}), 0.10, 500, provider="p3"),
    ]


def test_complexity_classification():
    assert IntelligentModelRouter.classify("hello") == TaskComplexity.SIMPLE
    assert IntelligentModelRouter.classify("research latest AI systems and provide sources") == TaskComplexity.RESEARCH
    assert IntelligentModelRouter.classify("design and implement a multi-step architecture") == TaskComplexity.COMPLEX


def test_capability_matching_prefers_capable_model():
    router = IntelligentModelRouter(models())
    decision = router.choose("research latest AI systems and provide sources")
    assert decision.model == "researcher"
    assert decision.complexity == TaskComplexity.RESEARCH


def test_health_aware_fallback():
    profiles = models()
    router = IntelligentModelRouter(profiles, health_check=lambda m: m.name != "fast")
    decision = router.choose("hello")
    assert decision.model == "reasoner"


def test_bounded_fallback_and_telemetry():
    router = IntelligentModelRouter(models(), max_attempts=2)
    calls = []

    def generate(goal, model):
        calls.append(model.name)
        if model.name == "fast":
            raise RuntimeError("temporary provider failure")
        return "ok"

    assert router.generate("hello", generate) == "ok"
    assert calls == ["fast", "reasoner"]
    assert router.telemetry.attempts == 2
    assert router.telemetry.fallback_count == 1


def test_all_failures_are_bounded():
    router = IntelligentModelRouter(models(), max_attempts=2)
    with pytest.raises(RuntimeError, match="all bounded model attempts failed"):
        router.generate("hello", lambda *_: (_ for _ in ()).throw(RuntimeError("down")))
    assert router.telemetry.attempts == 2
