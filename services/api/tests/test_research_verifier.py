from app.research_verifier import ResearchVerifier, SourceEvidence

def test_supported_with_provenance():
    r = ResearchVerifier().verify(["Python is widely used for machine learning"], [SourceEvidence("s1", "Python is widely used for machine learning", "https://a.example", .9)])
    assert r.supported and r.source_ids == ("s1",)

def test_conflict_is_disputed():
    r = ResearchVerifier().verify(["Alpha is faster than Beta"], [SourceEvidence("s1", "Alpha is faster than Beta", "https://a.example", .9), SourceEvidence("s2", "Alpha is slower than Beta", "https://b.example", .9)])
    assert r.disputed == ("Alpha is faster than Beta",)

def test_unsupported_is_not_promoted():
    r = ResearchVerifier().verify(["Aethon has reached human-level general intelligence"], [SourceEvidence("s1", "Aethon is a research project", "https://a.example", .9)])
    assert r.unsupported and not r.supported

def test_non_http_source_is_ignored():
    r = ResearchVerifier().verify(["Python is widely used for machine learning"], [SourceEvidence("x", "Python is widely used for machine learning", "file:///tmp/x", 1)])
    assert r.unsupported
