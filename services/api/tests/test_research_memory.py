from app.memory_engine import PersistentMemoryEngine
from app.memory_repository import MemoryRepository
from app.research_memory import ResearchMemoryBridge
from app.web_research import ResearchReport, ResearchSource, WebResearchAgent


def test_research_is_stored_with_source_provenance():
    def search(query, limit):
        return [{"title": "A", "url": "https://example.com/a", "snippet": "fact A"}]

    researcher = WebResearchAgent(search, lambda url: "full fact A")
    repository = MemoryRepository(fallback=PersistentMemoryEngine())
    result = ResearchMemoryBridge(researcher, repository).research_and_store(
        "research A", owner_id="alice", project_id="p", namespace="research"
    )
    assert len(result.stored_memory_ids) == 1
    found = repository.search("full fact A", owner_id="alice", project_id="p", namespace="research")
    assert len(found) == 1
    assert "https://example.com/a" in found[0].content
    assert found[0].source == "web_research"


def test_research_memory_is_scoped():
    source = ResearchSource("A", "https://example.com/a", content="fact A")
    report = ResearchReport("q", [source], ["fact A"])
    researcher = WebResearchAgent(lambda q, n: [], lambda u: "")
    repository = MemoryRepository(fallback=PersistentMemoryEngine())
    bridge = ResearchMemoryBridge(researcher, repository)
    stored = bridge.research_and_store("q", owner_id="alice", project_id="p", namespace="research")
    assert stored.stored_memory_ids == ()

    memory_id = bridge._memory_id(source.url, report.query)
    repository.put(memory_id, "Research source: A\nURL: https://example.com/a\nEvidence: fact A",
                   owner_id="alice", project_id="p", namespace="research", memory_type="episodic",
                   source="web_research", confidence=0.8)
    assert repository.search("fact A", owner_id="bob", project_id="p", namespace="research") == []


def test_synthesis_uses_same_source_identity_as_memory():
    source = ResearchSource("Python", "https://example.com/python", content="Python 3.14 was released")
    report = ResearchReport("python release", [source], [])
    bridge = ResearchMemoryBridge(WebResearchAgent(lambda q, n: [], lambda u: ""), MemoryRepository(fallback=PersistentMemoryEngine()))
    result = bridge.synthesize_from_report(report, ["Python 3.14 was released"])
    assert result.claims[0].supported is True
    assert result.claims[0].source_ids == (bridge._memory_id(source.url, report.query),)
