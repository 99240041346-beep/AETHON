from typing import Any, Protocol
from aethon.schemas import Task, ToolRequest, ToolResult

class ModelProvider(Protocol):
    name: str
    def generate(self, prompt: str) -> str: ...

class DeterministicProvider:
    name = 'deterministic'
    def generate(self, prompt: str) -> str:
        return f'AETHON received: {prompt}'

class ModelRouter:
    def __init__(self, provider: ModelProvider | None = None):
        self.provider = provider or DeterministicProvider()
    def generate(self, prompt: str) -> str:
        return self.provider.generate(prompt)
