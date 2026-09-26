from app.memory_commands import NaturalMemory
from app.research_engine import ResearchEngine


def test_memory_policy_blocks_sensitive_explicit_content():
    memory = NaturalMemory()
    try:
        memory.execute(memory.parse("remember my Aadhaar number is 1234") , owner_id="owner")
    except Exception as exc:
        assert "eligible" in str(exc)
    else:
        raise AssertionError("sensitive memory was stored")


def test_research_engine_returns_structured_https_citations():
    class Search:
        def __call__(self, query, limit):
            return [{"title": "Official source", "url": "https://example.gov/source", "snippet": "evidence", "source": "example"}]
    class Fetch:
        def __call__(self, url):
            return {"text": "full evidence"}

    result = ResearchEngine(Search(), Fetch()).run("test")
    assert result.verified_sources == 1
    citations = ResearchEngine.format_citations(result)
    assert citations[0]["url"] == "https://example.gov/source"
    assert citations[0]["evidence"] == "full evidence"
