import pytest

from app.skill_system import BoundedSkillSystem, Skill, SkillRegistry, SkillRequest, SkillSecurityError


def test_registry_is_bounded_and_case_insensitive():
    registry = SkillRegistry(max_skills=1)
    registry.register(Skill("Search", "safe search"))
    assert registry.get("search").name == "Search"
    with pytest.raises(SkillSecurityError):
        registry.register(Skill("Second", "another"))


def test_approval_prevents_handler_execution():
    registry = SkillRegistry()
    registry.register(Skill("deploy", "deployment", requires_approval=True))
    called = []
    system = BoundedSkillSystem(registry)
    result = system.execute([SkillRequest("deploy", "x")], {"deploy": lambda value: called.append(value) or "ok"})
    assert result[0].error == "approval required"
    assert not called


def test_failure_stops_following_skill():
    registry = SkillRegistry()
    registry.register(Skill("one", "first"))
    registry.register(Skill("two", "second"))
    system = BoundedSkillSystem(registry)
    result = system.execute([SkillRequest("one"), SkillRequest("two")], {"one": lambda _: (_ for _ in ()).throw(RuntimeError("boom")), "two": lambda _: "ok"})
    assert len(result) == 1
    assert result[0].success is False


def test_unknown_skill_and_input_budget_rejected():
    registry = SkillRegistry()
    registry.register(Skill("echo", "echo"))
    system = BoundedSkillSystem(registry, max_input=2)
    with pytest.raises(SkillSecurityError):
        system.validate([SkillRequest("missing")])
    with pytest.raises(SkillSecurityError):
        system.validate([SkillRequest("echo", "123")])


def test_plan_requires_goal_and_is_conservative():
    registry = SkillRegistry()
    system = BoundedSkillSystem(registry)
    assert system.plan("find information") == ()
    with pytest.raises(SkillSecurityError):
        system.plan(" ")
