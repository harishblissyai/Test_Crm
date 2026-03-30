"""
FastAPI dependencies for authentication, authorization, and tenant isolation.

Usage in route:
    @router.get("/protected")
    async def route(user: User = Depends(get_current_user)):
        ...

    @router.post("/admin-only")
    async def route(user: User = Depends(require_super_admin)):
        ...

    @router.get("/clients")
    async def route(tenant_id: uuid.UUID = Depends(require_tenant_context)):
        # tenant_id is always the operator's own tenant — no cross-tenant leakage
        ...
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validates the Bearer token and returns the authenticated User.
    Raises 401 on any invalid/expired token.
    """
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


# ── Role guards ────────────────────────────────────────────────────────────

async def require_super_admin(user: User = Depends(get_current_user)) -> User:
    """Only Super Admins may pass."""
    if not user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin access required",
        )
    return user


async def require_operator(user: User = Depends(get_current_user)) -> User:
    """Operators and Super Admins may pass."""
    if not user.is_operator and not user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator access required",
        )
    return user


# ── Tenant isolation ───────────────────────────────────────────────────────

async def require_tenant_context(user: User = Depends(require_operator)) -> uuid.UUID:
    """
    Returns the operator's tenant_id — enforces tenant isolation on every route.
    Super Admins without a tenant_id must use admin routes instead.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not associated with a tenant. Contact Super Admin.",
        )
    return user.tenant_id


async def verify_client_access(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
):
    """
    Shared dependency: loads a Client and verifies the caller has access to it.
    - Super Admins can access any client.
    - Operators can only access clients in their own tenant.

    Returns the Client object so it can be used directly in the route handler.
    Import Client here lazily to avoid circular imports at module load.
    """
    from app.models.client import Client

    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    if not user.is_super_admin and str(client.tenant_id) != str(user.tenant_id):
        # Return 404 instead of 403 — don't reveal that the client exists in another tenant
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    return client
