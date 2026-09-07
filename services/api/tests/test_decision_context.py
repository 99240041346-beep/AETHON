from app.decision_context import DecisionContextBuilder


class Memory:
    def __init__(self, content):
        self.content = content


def test_context_is_bounded_and_deduplicated():
    builder = DecisionContextBuilder(max_items=2, max_chars=100)
    result = builder.build([Memory("Fact A"), Memory("fact a"), Memory("Fact B"), Memory("Fact C")])
    assert result.memories == ("Fact A", "Fact B")


def test_empty_memory_is_ignored():
    result = DecisionContextBuilder().build([Memory(""), Memory("Useful context")])
    assert result.memories == ("Useful context",)


def test_memory_is_truncated():
    result = DecisionContextBuilder(max_chars=100).build([Memory("x" * 200)])
    assert len(result.memories[0]) == 100
