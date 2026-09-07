from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Callable, Iterable

class TaskComplexity(str, Enum):
    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"
    RESEARCH = "research"

@dataclass(frozen=True)
class ModelProfile:
    name: str
    capabilities: frozenset[str] = frozenset({"general"})
    cost_per_1k: float = 0.0
    latency_ms: int = 1000
    priority: int = 5
    provider: str = "unknown"
    healthy: bool = True

@dataclass(frozen=True)
class RoutingDecision:
    model: str
    provider: str
    complexity: TaskComplexity
    reason: str
    candidates: tuple[str, ...]

@dataclass
class RoutingTelemetry:
    attempts: int = 0
    successes: int = 0
    failures: int = 0
    fallback_count: int = 0
    latencies_ms: list[float] = field(default_factory=list)

class IntelligentModelRouter:
    """Deterministic, bounded model selection with health-aware fallbacks."""
    def __init__(self, models: Iterable[ModelProfile], *, max_attempts: int = 3, health_check: Callable[[ModelProfile], bool] | None = None):
        self.models = tuple(models)
        if not self.models: raise ValueError("at least one model profile is required")
        if not 1 <= max_attempts <= 5: raise ValueError("max_attempts must be between 1 and 5")
        self.max_attempts = max_attempts
        self.health_check = health_check or (lambda model: model.healthy)
        self.telemetry = RoutingTelemetry()

    @staticmethod
    def classify(goal: str) -> TaskComplexity:
        text = goal.strip().lower()
        if not text: raise ValueError("goal must not be empty")
        if any(term in text for term in ("research", "latest", "sources", "compare studies", "investigate")): return TaskComplexity.RESEARCH
        if any(term in text for term in ("architect", "debug", "analyze", "design", "multi-step", "implement")) or len(text.split()) > 40: return TaskComplexity.COMPLEX
        if len(text.split()) <= 8: return TaskComplexity.SIMPLE
        return TaskComplexity.STANDARD

    @staticmethod
    def _required_capabilities(complexity: TaskComplexity) -> frozenset[str]:
        return {TaskComplexity.SIMPLE: frozenset({"general"}), TaskComplexity.STANDARD: frozenset({"general"}), TaskComplexity.COMPLEX: frozenset({"general", "reasoning"}), TaskComplexity.RESEARCH: frozenset({"general", "reasoning", "research"})}[complexity]

    def rank(self, goal: str) -> tuple[ModelProfile, ...]:
        required = self._required_capabilities(self.classify(goal))
        healthy = [m for m in self.models if self.health_check(m) and required.issubset(m.capabilities)]
        if not healthy: healthy = [m for m in self.models if self.health_check(m)]
        if not healthy: raise RuntimeError("no healthy model is available")
        return tuple(sorted(healthy, key=lambda m: (m.cost_per_1k, m.latency_ms, -m.priority, m.name)))

    def choose(self, goal: str) -> RoutingDecision:
        complexity = self.classify(goal); candidates = self.rank(goal); chosen = candidates[0]
        return RoutingDecision(chosen.name, chosen.provider, complexity, f"{complexity.value} task; selected lowest cost/latency healthy capable model", tuple(m.name for m in candidates))

    def generate(self, goal: str, generate_fn: Callable[[str, ModelProfile], str]) -> str:
        candidates = self.rank(goal); last_error: Exception | None = None
        for index, model in enumerate(candidates[:self.max_attempts]):
            self.telemetry.attempts += 1; started = time.perf_counter()
            try:
                if not self.health_check(model): raise RuntimeError(f"model unhealthy: {model.name}")
                result = generate_fn(goal, model)
                if not isinstance(result, str) or not result.strip(): raise RuntimeError("model returned an empty result")
                self.telemetry.successes += 1; self.telemetry.latencies_ms.append((time.perf_counter()-started)*1000)
                if index: self.telemetry.fallback_count += 1
                return result
            except Exception as exc:
                self.telemetry.failures += 1; self.telemetry.latencies_ms.append((time.perf_counter()-started)*1000); last_error = exc
        raise RuntimeError(f"all bounded model attempts failed: {last_error}") from last_error
