from aethon.agent_learning import AgentLearning, LearningSignal


def test_unverified_outcome_creates_no_learning_signal():
    assert AgentLearning().from_outcome(goal="g", result="r", verified=False) == ()


def test_verified_outcome_is_bounded():
    signals = AgentLearning(max_chars=100).from_outcome(goal="goal", result="x" * 200, verified=True)
    assert len(signals) == 1
    assert len(signals[0].value) <= 100 + len("Goal: goal\nResult: ")
    assert signals[0].confidence == 1.0


def test_learning_signals_are_deduplicated_and_bounded():
    learning = AgentLearning(max_signals=2)
    signals = learning.deduplicate([
        LearningSignal("a", "one"),
        LearningSignal("a", "ONE"),
        LearningSignal("b", "two"),
        LearningSignal("c", "three"),
    ])
    assert signals == (LearningSignal("a", "one"), LearningSignal("b", "two"))
