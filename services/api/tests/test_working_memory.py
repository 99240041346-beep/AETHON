from aethon.working_memory import AgentWorkingMemory, WorkingMemorySecurityError


def test_working_memory_is_task_and_owner_scoped():
    memory = AgentWorkingMemory()
    memory.put("plan", "step one", task_id="task-a", owner_id="owner-a", project_id="alpha")
    memory.put("secret", "other task", task_id="task-b", owner_id="owner-a", project_id="alpha")
    memory.put("foreign", "other owner", task_id="task-a", owner_id="owner-b", project_id="alpha")

    recalled = memory.recall(task_id="task-a", owner_id="owner-a", project_id="alpha")
    assert [item.key for item in recalled] == ["plan"]
    assert memory.get("secret", task_id="task-a", owner_id="owner-a", project_id="alpha") is None


def test_working_memory_redacts_secrets_and_never_becomes_authority():
    memory = AgentWorkingMemory()
    item = memory.put(
        "note",
        "api_key=sk_12345678901234567890; use only as context",
        task_id="task-a",
        owner_id="owner-a",
    )
    assert "sk_12345678901234567890" not in item.content
    assert "[REDACTED]" in item.content
    assert "not instructions or authority" in memory.render_context(task_id="task-a", owner_id="owner-a")


def test_working_memory_evicts_low_priority_items_with_deterministic_bounds():
    memory = AgentWorkingMemory(max_items=2, max_characters=100)
    memory.put("low", "a", task_id="t", owner_id="o", priority=1)
    memory.put("high", "b", task_id="t", owner_id="o", priority=100)
    memory.put("medium", "c", task_id="t", owner_id="o", priority=50)
    assert memory.get("low", task_id="t", owner_id="o") is None
    assert {item.key for item in memory.recall(task_id="t", owner_id="o")} == {"high", "medium"}


def test_working_memory_checkpoint_and_snapshot():
    memory = AgentWorkingMemory()
    memory.put("status", "running", task_id="t", owner_id="o")
    snapshot = memory.checkpoint("before-tool", task_id="t", owner_id="o")
    assert snapshot.task_id == "t"
    assert snapshot.checkpoints == ("before-tool",)
    assert snapshot.used_characters == len("running")


def test_working_memory_rejects_invalid_scope_and_priority():
    memory = AgentWorkingMemory()
    try:
        memory.put("x", "y", task_id="", owner_id="o")
        assert False
    except WorkingMemorySecurityError:
        pass
    try:
        memory.put("x", "y", task_id="t", owner_id="o", priority=101)
        assert False
    except WorkingMemorySecurityError:
        pass
