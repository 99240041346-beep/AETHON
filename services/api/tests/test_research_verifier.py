from app.research_verifier import ResearchVerifier, SourceEvidence


def test_support_and_provenance():
    result = ResearchVerifier().verify(
        ["Python is widely used for machine learning"],
        [SourceEvidence("s1", "Python is widely used for machine learning", "https://a.example", 0.9)],
    )
    assert result.supported == ("Python is widely used for machine learning",)
    assert result.source_ids == ("s1",)


def test_conflicting_sources_are_disputed():
    result = ResearchVerifier().verify(
        ["Alpha system is faster than Beta system"],
        [
            SourceEvidence("s1", "Alpha system is faster than Beta system", "https://a.example", 0.9),
            SourceEvidence("s2", "Alpha system is slower than Beta system", "https://b.example", 0.9),
        ],
    )
    assert result.disputed == ("Alpha system is faster than Beta system",)


def test_unsupported_claim_is_not_promoted():
    result = ResearchVerifier().verify(
        ["Aethon has reached human-level general intelligence"],
        [SourceEvidence("s1", "Aethon is a research project", "https://a.example", 0.9)],
    )
    assert result.unsupported
    assert not result.supported


def test_untrusted_urls_are_ignored():
    result = ResearchVerifier().verify(
        ["Python is widely used for machine learning"],
        [SourceEvidence("x", "Python is widely used for machine learning", "file:///tmp/a", 1.0)],
    )
    assert result.unsupported
