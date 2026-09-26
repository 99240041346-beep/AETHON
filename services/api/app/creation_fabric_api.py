from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aethon.auth import current_owner, security
from aethon.creation_provider_fabric import CreationProviderFabric

router = APIRouter(prefix="/v1/creation-fabric", tags=["creation-fabric"])
fabric = CreationProviderFabric()


class CreationRequest(BaseModel):
    capability: str = Field(pattern=r"^(website|video|image|design|deploy)$")
    payload: dict = Field(default_factory=dict)
    provider: str | None = None


def owner(credentials=Depends(security)) -> str:
    return current_owner(credentials)


@router.get("/providers")
def providers(owner_id: str = Depends(owner)):
    return {"ok": True, "providers": [item.__dict__ for item in fabric.list()]}


@router.post("/dispatch")
def dispatch(request: CreationRequest, owner_id: str = Depends(owner)):
    try:
        result = fabric.dispatch(request.capability, request.payload, request.provider)
    except (RuntimeError, TypeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"ok": True, "owner_id": owner_id, **result.__dict__}
