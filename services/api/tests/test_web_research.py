from app.web_research import WebResearchAgent


def test_research_searches_fetches_and_builds_evidence():
    fetched = {"https://example.com/a": {"content": "Authoritative fact A."}, "https://example.com/b": "Fact B."}
    calls = []

    def search(query, limit):
        calls.append((query, limit))
        return [
            {"title": "A", "url": "https://example.com/a", "snippet": "snippet A", "source": "example"},
            {"title": "B", "url": "https://example.com/b", "snippet": "snippet B", "source": "example"},
        ]

    def fetch(url):
        return fetched[url]

    report = WebResearchAgent(search, fetch, max_sources=2).research("latest AI research")
    assert calls == [("latest AI research", 2)]
    assert [source.url for source in report.sources] == ["https://example.com/a", "https://example.com/b"]
    assert "Authoritative fact A." in report.evidence[0]
    assert "Fact B." in report.evidence[1]


def test_research_ignores_non_http_results():
    report = WebResearchAgent(lambda q, n: [{"title": "bad", "url": "file:///tmp/a"}], lambda u: "x").research("query")
    assert report.sources == []
    assert report.limitations == ["No usable public-web sources were returned."]


def test_research_records_fetch_failure_without_aborting():
    def search(q, n):
        return [{"title": "A", "url": "https://example.com/a", "snippet": "fallback evidence"}]

    def fetch(url):
        raise TimeoutError("timeout")

    report = WebResearchAgent(search, fetch).research("query")
    assert len(report.sources) == 1
    assert report.evidence == ["[A] fallback evidence (source: https://example.com/a)"]
    assert "Could not fetch https://example.com/a: TimeoutError" in report.limitations


def test_empty_query_is_rejected():
    try:
        WebResearchAgent(lambda q, n: [], lambda u: "").research("  ")
    except ValueError as exc:
        assert str(exc) == "query must not be empty"
    else:
        raise AssertionError("expected ValueError")
