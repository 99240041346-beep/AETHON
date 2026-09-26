from __future__ import annotations

import pytest
from aethon.intent_analyzer import IntentAnalyzer, IntentType

@pytest.fixture()
def analyzer() -> IntentAnalyzer:
    return IntentAnalyzer()

@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("what is Aadhaar update?", IntentType.RESEARCH),
        ("compare Android and iPhone", IntentType.RESEARCH),
        ("remember that I use Python", IntentType.MEMORY),
        ("forget that memory", IntentType.MEMORY),
        ("analyze this CSV", IntentType.DATA_ANALYSIS),
        ("fix this traceback in my code", IntentType.CODING),
        ("create a project for crop monitoring", IntentType.PROJECT),
        ("break this project into tasks", IntentType.TASK),
        ("send an email to the team", IntentType.EXTERNAL_ACTION),
        ("open YouTube", IntentType.DEVICE_ACTION),
        ("generate an image of a farm", IntentType.IMAGE_GENERATION),
        ("create an AI video for my project", IntentType.VIDEO_GENERATION),
        ("design a social post for my project", IntentType.DESIGN_GENERATION),
        ("build a website for my farm", IntentType.WEBSITE_GENERATION),
        ("write a report about the experiment", IntentType.DOCUMENT_GENERATION),
        ("schedule this every week", IntentType.AUTOMATION),
    ],
)
def test_common_intents(analyzer: IntentAnalyzer, text: str, expected: IntentType) -> None:
    assert analyzer.analyze(text).intent is expected

def test_contextual_reference_is_marked_without_inventing_target(analyzer: IntentAnalyzer) -> None:
    result = analyzer.analyze("what about the price?", context="Previous answer described a product.")
    assert result.intent is IntentType.NORMAL_CHAT
    assert result.arguments == {"needs_context": True}

def test_side_effects_require_confirmation(analyzer: IntentAnalyzer) -> None:
    result = analyzer.analyze("send an email to user@example.com")
    assert result.intent is IntentType.EXTERNAL_ACTION
    assert result.requires_confirmation is True

def test_empty_input_is_rejected(analyzer: IntentAnalyzer) -> None:
    with pytest.raises(ValueError): analyzer.analyze("   ")