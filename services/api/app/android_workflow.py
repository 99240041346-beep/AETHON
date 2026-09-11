from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MAX_WORKFLOW_STEPS = 8
MAX_SELECTOR_LENGTH = 200

@dataclass(frozen=True)
class AndroidWorkflowStep:
    capability: str
    arguments: dict[str, Any]
    verify: dict[str, Any] | None = None

class AndroidWorkflowPlanner:
    """Bounded planner; emits only allowlisted Android capabilities."""

    ALLOWED_CAPABILITIES = {
        "OPEN_APP", "SCREEN_READ", "SCREEN_CLICK", "SCREEN_SCROLL",
        "SCREEN_TEXT", "SCREEN_BACK",
    }

    def plan(self, text: str) -> list[AndroidWorkflowStep]:
        value = text.strip().lower()
        if not value:
            raise ValueError("workflow text cannot be empty")
        if "settings" in value and any(term in value for term in ("wi-fi", "wifi", "wi fi")):
            return [
                AndroidWorkflowStep("OPEN_APP", {"package": "com.android.settings", "app": "Settings"}),
                AndroidWorkflowStep("SCREEN_READ", {"maxNodes": 250}, {"contains_any": ["Wi-Fi", "Wi-Fi and internet", "Network & internet"]}),
                AndroidWorkflowStep("SCREEN_CLICK", {"text": "Wi-Fi"}),
                AndroidWorkflowStep("SCREEN_READ", {"maxNodes": 250}, {"contains_any": ["Wi-Fi", "Wi-Fi network"]}),
            ]
        raise ValueError("no bounded Android workflow is available for this request")

    @staticmethod
    def encode(steps: list[AndroidWorkflowStep]) -> list[dict[str, Any]]:
        if not steps or len(steps) > MAX_WORKFLOW_STEPS:
            raise ValueError("workflow exceeds bounded step limit")
        encoded: list[dict[str, Any]] = []
        for step in steps:
            if step.capability not in AndroidWorkflowPlanner.ALLOWED_CAPABILITIES:
                raise ValueError("workflow contains an unsupported capability")
            if not isinstance(step.arguments, dict):
                raise ValueError("workflow arguments must be an object")
            for key in ("text", "description", "className", "packageName"):
                value = step.arguments.get(key)
                if value is not None and (not isinstance(value, str) or len(value) > MAX_SELECTOR_LENGTH):
                    raise ValueError("workflow selector is invalid or too long")
            if step.capability == "SCREEN_READ":
                max_nodes = step.arguments.get("maxNodes", 250)
                if not isinstance(max_nodes, int) or not 1 <= max_nodes <= 250:
                    raise ValueError("SCREEN_READ maxNodes must be between 1 and 250")
            if step.capability == "SCREEN_TEXT":
                value = step.arguments.get("value", "")
                if not isinstance(value, str) or len(value) > 2000:
                    raise ValueError("SCREEN_TEXT value is invalid or too long")
            encoded.append({"capability": step.capability, "arguments": dict(step.arguments), "verify": step.verify})
        return encoded

    @staticmethod
    def verify(step: dict[str, Any], result: dict[str, Any]) -> bool:
        expected = step.get("verify") or {}
        if not expected:
            return True
        values: list[str] = []
        nodes = result.get("nodes") if isinstance(result, dict) else None
        if isinstance(nodes, list):
            for node in nodes[:250]:
                if isinstance(node, dict):
                    for key in ("text", "description", "class", "package"):
                        item = node.get(key)
                        if item:
                            values.append(str(item)[:300])
        blob = " ".join(values).casefold()
        contains_any = expected.get("contains_any", [])
        return isinstance(contains_any, list) and any(
            isinstance(item, str) and item and item.casefold() in blob for item in contains_any
        )
