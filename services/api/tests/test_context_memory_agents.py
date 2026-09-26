from aethon.agent_catalog import get_builtin_agent
from aethon.astra_core import Permission
from aethon.context import ContextManager, ContextState
from aethon.memory_policy import MemoryPolicy

def test_context_is_bounded_and_resolves_project():
    state = ContextState(project={"id": "p1"})
    manager = ContextManager(max_messages=2)
    for i in range(4):
        manager.add_message(state, {"text": str(i)})
    assert [m["text"] for m in state.conversation] == ["2", "3"]
    assert manager.resolve_reference("do this for the project", state)["value"]["id"] == "p1"

def test_memory_requires_explicit_request_and_rejects_sensitive_by_default():
    policy = MemoryPolicy()
    assert policy.extract("I use Python") is None
    candidate = policy.extract("remember that I use Python")
    assert candidate and policy.can_store(candidate)
    sensitive = policy.extract("remember my Aadhaar number")
    assert sensitive and sensitive.sensitive
    assert not policy.can_store(sensitive)

def test_all_builtin_agents_share_common_definition():
    for name in ("research", "coding", "data", "document", "writing", "study", "project", "automation"):
        agent = get_builtin_agent(name)
        assert agent.id == name
        assert agent.max_steps > 0
        assert Permission.READ in agent.permissions
