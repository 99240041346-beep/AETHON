from aethon.brain import AgentBrain, PlanStepKind


def test_web_goal_gets_search_fetch_and_verify_plan():
    plan = AgentBrain(max_steps=8).plan(
        "Research the latest developments and summarize them", ["web_search", "web_fetch"]
    )
    kinds = [step.kind for step in plan.steps]
    assert PlanStepKind.SEARCH in kinds
    assert PlanStepKind.FETCH in kinds
    assert kinds[-1] is PlanStepKind.VERIFY
    assert len(plan.steps) <= 8


def test_math_goal_selects_calculator():
    plan = AgentBrain().plan("Calculate the average of these numbers", ["calculator"])
    assert any(step.tool == "calculator" for step in plan.steps)


def test_replan_is_bounded_and_non_destructive():
    brain = AgentBrain(max_steps=4)
    plan = brain.plan("answer a question", [])
    replanned = brain.replan(plan, "verification failed")
    assert len(replanned.steps) <= 4
    assert replanned.steps[: len(plan.steps)] == plan.steps


def test_empty_goal_rejected():
    try:
        AgentBrain().plan("   ", [])
    except ValueError as exc:
        assert "goal" in str(exc)
    else:
        raise AssertionError("empty goal must be rejected")
