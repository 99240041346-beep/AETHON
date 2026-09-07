from aethon.model_routing import IntelligentModelRouter, ModelProfile


def test_routing_only_selects_registered_profiles():
    router = IntelligentModelRouter([ModelProfile("known", frozenset({"general"}), 0.01, 100)])
    decision = router.choose("hello")
    assert decision.model == "known"
    assert "unknown" not in decision.candidates
