from fastapi import APIRouter, Depends, HTTPException

from aethon.auth import current_owner, security
from app.integration_registry import IntegrationRegistry


router = APIRouter(prefix="/v1/integrations", tags=["integrations"])
registry = IntegrationRegistry()


def owner(credentials=Depends(security)) -> str:
    return current_owner(credentials)


@router.get("")
def integrations(owner_id: str = Depends(owner)):
    return {"ok": True, "integrations": registry.list()}


@router.get("/{name}")
def integration(name: str, owner_id: str = Depends(owner)):
    result = registry.get(name)
    if result is None:
        raise HTTPException(404, "integration not found")
    return {"ok": True, "integration": result}
