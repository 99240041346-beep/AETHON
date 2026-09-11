from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MAX_WORKFLOW_STEPS = 8

@dataclass(frozen=True)
class AndroidWorkflowStep:
    capability: str
    arguments: dict[str, Any]
    verify: dict[str, Any] | None = None

class AndroidWorkflowPlanner:
    """Bounded planner; emits only allowlisted Android capabilities."""

    def plan(self, text: str) -> list[AndroidWorkflowStep]:
        value = text.strip().lower()
        if not value:
            raise ValueError("workflow text cannot be empty")
        if "settings" in value and any(term in value for term in ("wi-fi", "wifi", "wi fi")):
            return [
                AndroidWorkflowStep("OPEN_APP", {"package": "com.android.settings", "app": "Settings"}),
                AndroidWorkflowStep("SCREEN_READ", {"maxNodes": 250}, {"contains_any": ["Wi-Fi", "Wi-Fi and internet", "Network & internet"]}),
                AndroidWorkflowStep("SCREEN_CLICK", {"text": "Wi-Fi"}, {"screen_contains_any": ["Wi-Fi", "Wi-Fi network"]}),
                AndroidWorkflowStep("SCREEN_READ", {"maxNodes": 250}, {"contains_any": ["Wi-Fi", "Wi-Fi network"]}),
            ]
        raise ValueError("no bounded Android workflow is available for this request")

    @staticmethod
    def encode(steps: list[AndroidWorkflowStep]) -> list[dict[str, Any]]:
        if not steps or len(steps) > MAX_WORKFLOW_STEPS:
            raise ValueError("workflow exceeds bounded step limit")
        return [{"capability": s.capability, "arguments": s.arguments, "verify": s.verify} for s in steps]

    @staticmethod
    def verify(step: dict[str, Any], result: dict[str, Any]) -> bool:
        expected = step.get("verify") or {}
        if not expected:
            return True
        values: list[str] = []
        nodes = result.get("nodes") if isinstance(result, dict) else None
        if isinstance(nodes, list):
            for node in nodes:
                if isinstance(node, dict):
                    for key in ("text", "description", "class", "package"):
                        item = node.get(key)
                        if item:
                            values.append(str(item))
        blob = " ".join(values).casefold()
        return any(str(item).casefold() in blob for item in expected.get("contains_any", [])) or any(str(item).casefold() in blob for item in expected.get("screen_contains_any", []))
