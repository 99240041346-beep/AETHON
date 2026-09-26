from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aethon.auth import current_owner, security
from aethon.ai_provider_fabric import AIProviderError, AIProviderFabric

router = APIRouter(prefix="/v1/ai-fabric", tags=["ai-fabric"])
fabric = AIProviderFabric()


class AIGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=50000)
    provider: str | None = Field(default=None, max_length=80)


def owner(credentials=Depends(security)) -> str:
    return current_owner(credentials)


@router.get("/providers")
def providers(owner_id: str = Depends(owner)):
    return {"ok": True, "providers": [item.__dict__ for item in fabric.list()],
            "capabilities": fabric.capabilities()}


@router.post("/generate")
def generate(request: AIGenerateRequest, owner_id: str = Depends(owner)):
    try:
        result = fabric.generate(request.prompt, provider=request.provider)
    except AIProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"ok": True, "owner_id": owner_id, "provider": result.provider,
            "model": result.model, "text": result.text, "live": result.live,
            "metadata": result.metadata}
