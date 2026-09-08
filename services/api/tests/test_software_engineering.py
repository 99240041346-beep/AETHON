from app.software_engineering import (
    BoundedSoftwareEngineeringAgent,
    SoftwareOperation,
    SoftwareRequest,
    SoftwareResult,
    SoftwareSecurityError,
)


class Adapter:
    def __init__(self, failures=()):
        self.calls = []
        self.failures = set(failures)

    def execute(self, request):
        self.calls.append(request)
        if request.operation in self.failures:
            return SoftwareResult(request.operation, request.path, False, error="failed")
        return SoftwareResult(request.operation, request.path, True, output="ok")


def test_path_validation_is_bounded_and_fail_closed():
    agent = BoundedSoftwareEngineeringAgent(workspace="repo")
    assert agent.validate_path("repo/src/main.py") == "repo/src/main.py"
    try:
        agent.validate_path("../secret.txt")
        assert False
    except SoftwareSecurityError:
        pass
    try:
        agent.validate_path("/etc/passwd")
        assert False
    except SoftwareSecurityError:
        pass


def test_approval_gate_does_not_execute_unapproved_operation():
    agent = BoundedSoftwareEngineeringAgent()
    adapter = Adapter()
    results = agent.execute(
        [SoftwareRequest(SoftwareOperation.WRITE, "src/a.py", "x", requires_approval=True)],
        adapter,
    )
    assert results[0].error == "approval required"
    assert adapter.calls == []


def test_failed_operation_stops_remaining_work():
    agent = BoundedSoftwareEngineeringAgent()
    adapter = Adapter({SoftwareOperation.RUN_TESTS})
    requests = [
        SoftwareRequest(SoftwareOperation.RUN_TESTS),
        SoftwareRequest(SoftwareOperation.WRITE, "src/a.py", "x"),
    ]
    results = agent.execute(requests, adapter)
    assert len(results) == 1
    assert len(adapter.calls) == 1


def test_operation_budget_and_content_limits():
    agent = BoundedSoftwareEngineeringAgent(max_operations=1, max_content=3)
    try:
        agent.validate_requests([SoftwareRequest(SoftwareOperation.DIFF), SoftwareRequest(SoftwareOperation.DIFF)])
        assert False
    except SoftwareSecurityError:
        pass
    try:
        agent.validate_requests([SoftwareRequest(SoftwareOperation.WRITE, "a.py", "long")])
        assert False
    except SoftwareSecurityError:
        pass


def test_plan_is_conservative_and_requires_goal():
    agent = BoundedSoftwareEngineeringAgent()
    assert agent.plan("fix tests")[0].operation is SoftwareOperation.DIFF
    try:
        agent.plan(" ")
        assert False
    except SoftwareSecurityError:
        pass
