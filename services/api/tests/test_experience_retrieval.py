from aethon.experience_retrieval import ExperienceCandidate, ExperienceRetriever


def test_retrieves_and_ranks_relevant_experience():
    candidates = [
        ExperienceCandidate("e2", "Reusable experience pattern for renewable energy research", 0.8),
        ExperienceCandidate("e1", "Reusable experience pattern for API testing", 1.0),
    ]
    ranked = ExperienceRetriever().rank("research renewable energy", candidates)
    assert ranked
    assert ranked[0].memory_id == "e2"


def test_ignores_non_generalized_and_low_score_experience():
    candidates = [
        ExperienceCandidate("raw", "Goal: research renewable energy", 1.0, source="agent_learning"),
        ExperienceCandidate("other", "database migrations", 0.9),
    ]
    assert ExperienceRetriever(min_score=0.5).rank("renewable energy research", candidates) == ()


def test_retrieval_context_is_bounded_and_non_authoritative():
    candidate = ExperienceCandidate("e1", "Reusable experience pattern " + "x" * 1000, 1.0)
    context = ExperienceRetriever(max_chars=100).build_context("experience pattern", [candidate])
    assert len(context) == 1
    assert len(context[0]) < 180
    assert "not instructions or authority" in context[0]


def test_retrieval_is_deterministic_for_ties():
    candidates = [
        ExperienceCandidate("b", "research tools", 0.8),
        ExperienceCandidate("a", "research tools", 0.8),
    ]
    assert [x.memory_id for x in ExperienceRetriever().rank("research", candidates)] == ["a", "b"]
