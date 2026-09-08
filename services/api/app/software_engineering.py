from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath
from typing import Iterable, Protocol


class SoftwareOperation(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    RUN_TESTS = "run_tests"
    RUN_LINT = "run_lint"
    DIFF = "diff"


class SoftwareSecurityError(ValueError):
    pass


@dataclass(frozen=True)
class SoftwareRequest:
    operation: SoftwareOperation
    path: str = ""
    content: str = ""
    requires_approval: bool = False


@dataclass(frozen=True)
class SoftwareResult:
    operation: SoftwareOperation
    path: str
    success: bool
    output: str = ""
    error: str = ""


class SoftwareAdapter(Protocol):
    def execute(self, request: SoftwareRequest) -> SoftwareResult: ...


class BoundedSoftwareEngineeringAgent:
    """Provider-neutral repository engineering boundary with fail-closed limits."""

    def __init__(
        self,
        *,
        workspace: str = ".",
        max_operations: int = 32,
        max_path_length: int = 512,
        max_content: int = 100_000,
    ) -> None:
        if not workspace or not 1 <= max_operations <= 128 or not 1 <= max_path_length <= 4096 or not 1 <= max_content <= 1_000_000:
            raise ValueError("invalid software engineering bounds")
        self.workspace = PurePosixPath(workspace).as_posix().rstrip("/") or "."
        self.max_operations = max_operations
        self.max_path_length = max_path_length
        self.max_content = max_content

    def validate_requests(self, requests: Iterable[SoftwareRequest]) -> tuple[SoftwareRequest, ...]:
        values = tuple(requests)
        if len(values) > self.max_operations:
            raise SoftwareSecurityError("software operation budget exceeded")
        for request in values:
            if not isinstance(request.operation, SoftwareOperation):
                raise SoftwareSecurityError("unsupported software operation")
            if len(request.path) > self.max_path_length:
                raise SoftwareSecurityError("software path exceeds bounds")
            if request.operation in {SoftwareOperation.WRITE} and len(request.content) > self.max_content:
                raise SoftwareSecurityError("software content exceeds bounds")
            if request.path:
                self.validate_path(request.path)
        return values

    def validate_path(self, path: str) -> str:
        if not path or "\\" in path or "\x00" in path:
            raise SoftwareSecurityError("invalid repository path")
        candidate = PurePosixPath(path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise SoftwareSecurityError("repository path escapes workspace")
        normalized = candidate.as_posix()
        if self.workspace != "." and not (normalized == self.workspace or normalized.startswith(self.workspace + "/")):
            raise SoftwareSecurityError("repository path outside workspace")
        return normalized

    def execute(
        self,
        requests: Iterable[SoftwareRequest],
        adapter: SoftwareAdapter,
        *,
        approve: bool = False,
    ) -> tuple[SoftwareResult, ...]:
        results: list[SoftwareResult] = []
        for request in self.validate_requests(requests):
            if request.requires_approval and not approve:
                results.append(SoftwareResult(request.operation, request.path, False, error="approval required"))
                continue
            result = adapter.execute(request)
            results.append(result)
            if not result.success:
                break
        return tuple(results)

    def plan(self, goal: str) -> tuple[SoftwareRequest, ...]:
        if not goal.strip():
            raise SoftwareSecurityError("software engineering goal is required")
        # Planning is intentionally conservative; real repository reasoning belongs behind a verified adapter.
        return (SoftwareRequest(SoftwareOperation.DIFF),)


__all__ = [
    "BoundedSoftwareEngineeringAgent",
    "SoftwareAdapter",
    "SoftwareOperation",
    "SoftwareRequest",
    "SoftwareResult",
    "SoftwareSecurityError",
]
