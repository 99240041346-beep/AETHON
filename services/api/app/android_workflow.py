from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.android_ui_state import find_candidates, normalize_snapshot

MAX_WORKFLOW_STEPS = 8
MAX_SELECTOR_LENGTH = 200

@dataclass(frozen=True)
class AndroidWorkflowStep:
    capability: str
    arguments: dict[str, Any]
    verify: dict[str, Any] | None = None

class AndroidWorkflowPlanner:
    """Bounded deterministic planner for authorized semantic Android UI actions."""

    ALLOWED_CAPABILITIES = {"OPEN_APP", "SCREEN_READ", "SCREEN_CLICK", "SCREEN_SCROLL", "SCREEN_TEXT", "SCREEN_BACK"}
    APP_PACKAGES = {
        "settings": ("com.android.settings", "Settings"),
        "chrome": ("com.android.chrome", "Chrome"),
        "calculator": ("com.android.calculator2", "Calculator"),
        "clock": ("com.google.android.deskclock", "Clock"),
    }

    @staticmethod
    def _read() -> AndroidWorkflowStep:
        return AndroidWorkflowStep("SCREEN_READ", {"maxNodes": 250})

    @staticmethod
    def _selector(value: str) -> dict[str, str]:
        value = value.strip()
        if not value or len(value) > MAX_SELECTOR_LENGTH:
            raise ValueError("UI selector is invalid or too long")
        return {"text": value}

    def _open_and_click(self, app: str, target: str) -> list[AndroidWorkflowStep]:
        package, label = self.APP_PACKAGES[app]
        return [AndroidWorkflowStep("OPEN_APP", {"package": package, "app": label}), self._read(), AndroidWorkflowStep("SCREEN_CLICK", self._selector(target)), self._read()]

    def _open_and_type(self, app: str, target: str, value: str) -> list[AndroidWorkflowStep]:
        package, label = self.APP_PACKAGES[app]
        if not value or len(value) > 2000:
            raise ValueError("text input is invalid or too long")
        return [AndroidWorkflowStep("OPEN_APP", {"package": package, "app": label}), self._read(), AndroidWorkflowStep("SCREEN_TEXT", {**self._selector(target), "value": value}), self._read()]

    def plan(self, text: str) -> list[AndroidWorkflowStep]:
        value = text.strip()
        lower = value.casefold()
        if not value:
            raise ValueError("workflow text cannot be empty")
        if "settings" in lower and any(term in lower for term in ("wi-fi", "wifi", "wi fi")):
            return [
                AndroidWorkflowStep("OPEN_APP", {"package": "com.android.settings", "app": "Settings"}),
                AndroidWorkflowStep("SCREEN_READ", {"maxNodes": 250}, {"contains_any": ["Wi-Fi", "Wi-Fi and internet", "Network & internet"]}),
                AndroidWorkflowStep("SCREEN_CLICK", {"text": "Wi-Fi"}),
                AndroidWorkflowStep("SCREEN_READ", {"maxNodes": 250}, {"contains_any": ["Wi-Fi", "Wi-Fi network"]}),
            ]
        match = re.fullmatch(r"open\s+(settings|chrome|calculator|clock)\s+(?:and\s+)?(?:tap|click)\s+(.+)", value, re.IGNORECASE)
        if match:
            return self._open_and_click(match.group(1).casefold(), match.group(2).strip())
        match = re.fullmatch(r"open\s+(settings|chrome|calculator|clock)\s+(?:and\s+)?(?:type|enter)\s+(.+?)\s+(?:into|in)\s+(.+)", value, re.IGNORECASE)
        if match:
            return self._open_and_type(match.group(1).casefold(), match.group(3).strip(), match.group(2).strip())
        if re.fullmatch(r"(?:scroll|scroll down|scroll up)(?:\s+.+)?", lower):
            forward = "up" not in lower
            return [self._read(), AndroidWorkflowStep("SCREEN_SCROLL", {"forward": forward}), self._read()]
        if lower in {"go back", "back", "press back"}:
            return [self._read(), AndroidWorkflowStep("SCREEN_BACK", {}), self._read()]
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
            if step.capability == "SCREEN_SCROLL" and not isinstance(step.arguments.get("forward", True), bool):
                raise ValueError("SCREEN_SCROLL forward must be boolean")
            encoded.append({"capability": step.capability, "arguments": dict(step.arguments), "verify": step.verify})
        return encoded

    @staticmethod
    def select_action_candidate(step: dict[str, Any], result: dict[str, Any]) -> dict[str, Any] | None:
        """Resolve exactly one enabled semantic target from a SCREEN_READ snapshot; fail closed on ambiguity."""
        if not isinstance(step, dict) or not isinstance(result, dict):
            return None
        capability = step.get("capability")
        if capability not in {"SCREEN_CLICK", "SCREEN_TEXT", "SCREEN_SCROLL"}:
            return None
        arguments = step.get("arguments")
        if not isinstance(arguments, dict):
            return None
        try:
            state = normalize_snapshot(result)
        except (TypeError, ValueError):
            return None
        if not state.get("connected"):
            return None
        label = arguments.get("text") or arguments.get("description")
        if isinstance(label, str) and label.strip():
            candidates = find_candidates(state, label)
        elif capability == "SCREEN_SCROLL":
            candidates = [e for e in state["elements"] if e.get("enabled") and e.get("scrollable")]
        else:
            return None
        if len(candidates) != 1:
            return None
        candidate = candidates[0]
        if capability == "SCREEN_CLICK" and not candidate.get("clickable"):
            return None
        if capability == "SCREEN_TEXT" and not candidate.get("editable"):
            return None
        if capability == "SCREEN_SCROLL" and not candidate.get("scrollable"):
            return None
        return candidate

    @staticmethod
    def verify(step: dict[str, Any], result: dict[str, Any]) -> bool:
        expected = step.get("verify") or {}
        if not expected:
            return True
        try:
            state = normalize_snapshot(result)
        except (TypeError, ValueError):
            return False
        if not state.get("connected"):
            return False
        values: list[str] = []
        for element in state["elements"]:
            for key in ("text", "description", "class", "package"):
                item = element.get(key)
                if item:
                    values.append(str(item)[:300])
        blob = " ".join(values).casefold()
        contains_any = expected.get("contains_any", [])
        return isinstance(contains_any, list) and any(isinstance(item, str) and item and item.casefold() in blob for item in contains_any)
