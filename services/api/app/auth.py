from __future__ import annotations

import hashlib
import hmac
import os

from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)


def current_owner(credentials: HTTPAuthorizationCredentials | None) -> str:
    """Resolve the authenticated owner for protected resources.

    Production should configure both AETHON_API_TOKEN and AETHON_API_OWNER_ID.
    Development remains usable without credentials and is explicitly scoped to
    the local-dev owner. The token is compared using constant-time equality.
    """
    expected = os.getenv("AETHON_API_TOKEN")
    owner_id = os.getenv("AETHON_API_OWNER_ID", "local-dev").strip()
    if expected:
        if not credentials or credentials.scheme.lower() != "bearer" or not hmac.compare_digest(credentials.credentials, expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        return owner_id or "local-dev"
    return owner_id or "local-dev"


def token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
