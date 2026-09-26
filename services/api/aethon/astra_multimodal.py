from __future__ import annotations

"""ASTRA multimodal product facade over AETHON's canonical engine."""

from dataclasses import dataclass
from typing import Any
from app.multimodal import MediaInput, Modality, MultimodalEngine, MultimodalPacket

@dataclass(frozen=True)
class ASTRAObservation:
    modality: str
    content: Any
    metadata: dict[str, Any]

class ASTRAMultimodal:
    def __init__(self, engine: MultimodalEngine | None = None):
        self.engine = engine or MultimodalEngine()

    def build_packet(self, inputs: list[MediaInput], *, owner_id: str | None = None) -> MultimodalPacket:
        if not inputs or len(inputs) > 12:
            raise ValueError("inputs must contain between 1 and 12 media items")
        return self.engine.build_context(inputs)

    @staticmethod
    def observation(modality: Modality, content: Any, **metadata: Any) -> ASTRAObservation:
        return ASTRAObservation(modality=str(modality), content=content, metadata=metadata)
