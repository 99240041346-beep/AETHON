from aethon.experience_generalization import ExperienceEvidence, ExperienceGeneralizer


def test_repeated_verified_experiences_generalize():
    items = [
        ExperienceEvidence("m1", "Goal: research renewable energy adoption\nResult: verified"),
        ExperienceEvidence("m2", "Goal: research renewable energy adoption trends\nResult: verified"),
    ]
    patterns = ExperienceGeneralizer().generalize(items)
    assert len(patterns) == 1
    assert patterns[0].evidence_count == 2
    assert patterns[0].evidence_ids == ("m1", "m2")


def test_single_or_untrusted_evidence_does_not_generalize():
    assert ExperienceGeneralizer().generalize([
        ExperienceEvidence("m1", "Goal: research renewable energy adoption\nResult: verified"),
    ]) == ()
    assert ExperienceGeneralizer().generalize([
        ExperienceEvidence("m1", "Goal: research renewable energy adoption\nResult: untrusted", confidence=0.5),
        ExperienceEvidence("m2", "Goal: research renewable energy adoption trends\nResult: untrusted", confidence=0.5),
    ]) == ()


def test_conflicting_goals_are_not_overgeneralized():
    items = [
        ExperienceEvidence("a", "Goal: configure PostgreSQL connection pooling\nResult: verified"),
        ExperienceEvidence("b", "Goal: design a campus cultural festival\nResult: verified"),
    ]
    assert ExperienceGeneralizer().generalize(items) == ()


def test_generalization_is_bounded_and_scoped_by_input():
    items = [ExperienceEvidence(str(i), "Goal: build reliable API testing workflow\nResult: verified") for i in range(20)]
    patterns = ExperienceGeneralizer(max_patterns=1, max_chars=160).generalize(items)
    assert len(patterns) == 1
    assert len(patterns[0].pattern) <= 160
    assert patterns[0].evidence_count == 20
