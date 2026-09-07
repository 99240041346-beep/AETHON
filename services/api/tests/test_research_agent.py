from app.research_agent import IntegratedResearchAgent
from aethon.memory_engine import PersistentMemoryEngine
from aethon.memory_repository import MemoryRepository
from aethon.research_loop import AutonomousResearchLoop
from aethon.research_memory import ResearchMemoryBridge
from aethon.research_verifier import ResearchVerifier
from aethon.research_planner import AutonomousResearchPlanner
from aethon.web_research import ResearchReport, ResearchSource, WebResearchAgent


def test_integrated_agent_verifies_and_stores_research():
    source = ResearchSource("Source A", "https://example.com/a", content="Python is useful")
    report = ResearchReport("Python", [source], ["Python is useful"])
    researcher = WebResearchAgent(lambda q, n: [], lambda u: "")
    researcher.research = lambda q: report
    repository = MemoryRepository(fallback=PersistentMemoryEngine())
    bridge = ResearchMemoryBridge(researcher, repository)
    loop = AutonomousResearchLoop(AutonomousResearchPlanner(), researcher)
    result = IntegratedResearchAgent(loop, bridge, ResearchVerifier()).run(
        "Python", owner_id="alice", project_id="p"
    )
    assert result.verification.supported == ("Python is useful",)
    assert len(result.stored_memory_ids) == 1


def test_integrated_agent_preserves_scope():
    source = ResearchSource("Source", "https://example.com", content="scoped fact")
    report = ResearchReport("query", [source], ["scoped fact"])
    researcher = WebResearchAgent(lambda q, n: [], lambda u: "")
    researcher.research = lambda q: report
    repository = MemoryRepository(fallback=PersistentMemoryEngine())
    bridge = ResearchMemoryBridge(researcher, repository)
    loop = AutonomousResearchLoop(AutonomousResearchPlanner(), researcher)
    IntegratedResearchAgent(loop, bridge, ResearchVerifier()).run("query", owner_id="alice", project_id="p")
    assert repository.search("scoped fact", owner_id="bob", project_id="p", namespace="research") == []
