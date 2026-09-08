from app.reflection_quality import Reflection, ReflectionQualityEngine, ReflectionQualityError


def test_quality_is_deterministic_and_flags_failure():
    engine = ReflectionQualityEngine(min_score=60)
    quality = engine.evaluate(expected_steps=["a", "b"], completed_steps=["a"], failed_steps=["b"])
    assert quality.completeness == 50
    assert quality.score < 60
    assert engine.should_replan(quality)


def test_reflection_bounds_and_lessons():
    engine = ReflectionQualityEngine(max_items=2, max_text=10)
    result = engine.reflect(Reflection("done", "expected", failures=("bad",), lessons=("lesson", "extra")))
    assert len(result) == 2
    assert all(len(x) <= 10 for x in result)


def test_empty_expected_rejected():
    try:
        ReflectionQualityEngine().evaluate(expected_steps=[], completed_steps=[])
        assert False
    except ReflectionQualityError:
        pass
