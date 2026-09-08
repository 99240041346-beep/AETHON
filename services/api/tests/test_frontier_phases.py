from app.frontier_phases import BoundedFrontierEngine, CapabilityRequest, CapabilityResult, EvaluationCase, FrontierSecurityError, PhaseCapability, SkillRegistry


class Adapter:
    def __init__(self, success=True):
        self.success = success

    def execute(self, request):
        return CapabilityResult(request.capability, request.operation, self.success, output=request.payload if self.success else None, error="failed" if not self.success else "")


def test_all_remaining_capabilities_are_explicit():
    assert tuple(PhaseCapability) == (
        PhaseCapability.SOFTWARE, PhaseCapability.VOICE, PhaseCapability.REALTIME,
        PhaseCapability.SKILLS, PhaseCapability.EVALUATION, PhaseCapability.MODEL_ROUTING,
        PhaseCapability.HYBRID, PhaseCapability.DISTRIBUTED, PhaseCapability.IOT,
    )


def test_bounded_execution_and_approval():
    engine = BoundedFrontierEngine(max_operations=2)
    requests = [
        CapabilityRequest(PhaseCapability.SOFTWARE, "inspect", {"path": "src"}),
        CapabilityRequest(PhaseCapability.IOT, "actuate", {}, requires_approval=True),
    ]
    result = engine.execute(requests, {PhaseCapability.SOFTWARE: Adapter()})
    assert result[0].success
    assert result[1].error == "approval required"


def test_failure_stops_execution():
    engine = BoundedFrontierEngine()
    requests = [
        CapabilityRequest(PhaseCapability.VOICE, "speak", {}),
        CapabilityRequest(PhaseCapability.REALTIME, "stream", {}),
    ]
    result = engine.execute(requests, {PhaseCapability.VOICE: Adapter(False), PhaseCapability.REALTIME: Adapter()})
    assert len(result) == 1 and not result[0].success


def test_payload_and_evaluation_bounds():
    engine = BoundedFrontierEngine(max_payload_text=5)
    try:
        engine.validate([CapabilityRequest(PhaseCapability.HYBRID, "route", {"x": "123456"})])
        assert False
    except FrontierSecurityError:
        pass
    report = engine.evaluate([EvaluationCase("a", 1, 1), EvaluationCase("b", 1, 2)])
    assert report.passed == 1 and report.total == 2 and report.score == 50.0


def test_skill_registry_is_bounded_and_copying():
    registry = SkillRegistry(max_skills=1)
    registry.register("search", {"version": 1})
    metadata = registry.get("search")
    metadata["version"] = 2
    assert registry.get("search")["version"] == 1
    assert registry.names() == ("search",)
    try:
        registry.register("second", {})
        assert False
    except FrontierSecurityError:
        pass
