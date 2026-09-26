from aethon.astra_runtime import ASTRARuntime
from aethon.agent_catalog import get_builtin_agent
from aethon.schemas import ToolSpec, RiskClass


class FakeTools:
    def __init__(self, names):
        self._specs = [
            ToolSpec(
                name=name,
                description=name,
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                output_schema={},
                risk=RiskClass.LOW,
                side_effects=False,
                timeout_seconds=5,
                max_retries=0,
                authentication="owner",
                audit_required=False,
            )
            for name in names
        ]

    def list(self):
        return self._specs


def test_builtin_agent_catalog_is_stable():
    agent = get_builtin_agent("research")
    assert agent.id == "research"
    assert "web_research" in agent.tools


def test_astra_runtime_exposes_all_catalog_agents():
    runtime = ASTRARuntime(tools=FakeTools({"web.search", "web.fetch"}))
    ids = {item.id for item in runtime.agents()}
    assert {"research", "coding", "data", "document", "writing", "study", "project", "automation"} <= ids


def test_astra_runtime_rejects_uninstalled_capabilities_without_execution():
    runtime = ASTRARuntime(tools=FakeTools({"web_search", "web_fetch", "web_research"}))
    result = runtime.run(agent_id="research", goal="research a topic", owner_id="owner")
    assert result.status.value == "failed"
    assert "capability adapters unavailable" in (result.error or "")
