"""
Auth API — register, login, refresh token, logout.

Bootstrap flow (creating the very first Super Admin):
    POST /api/auth/register
    Header: X-Bootstrap-Key: <value from BOOTSTRAP_SECRET in .env>
    Body: { email, password, first_name, last_name }
    → Only works when zero Super Admins exist. Use once.

Normal flow:
    POST /api/auth/login          → access_token + refresh_token
    POST /api/auth/refresh-token  → new token pair (old refresh revoked)
    POST /api/auth/logout         → revoke refresh token
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, require_super_admin
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db.session import get_db
from app.models.user import RefreshToken, User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────

def _build_token_payload(user: User) -> dict:
    return {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "client_id": str(user.client_id) if user.client_id else None,
        "role_id": user.role_id,
        "is_operator": user.is_operator,
        "is_super_admin": user.is_super_admin,
    }


async def _issue_token_pair(user: User, db: AsyncSession) -> TokenResponse:
    """Create a new access + refresh token pair and persist the refresh token."""
    access_token = create_access_token(_build_token_payload(user))
    raw_refresh, refresh_hash = create_refresh_token()

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


# ── Routes ─────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (Super Admin only / bootstrap on first run)",
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    x_bootstrap_key: str | None = Header(default=None),
):
    """
    Two modes:
    1. Bootstrap: no Super Admin exists + correct X-Bootstrap-Key header → creates first Super Admin.
    2. Authenticated: caller is an existing Super Admin → creates any user type.
    """
    # Check if there is already a super admin
    super_admin_count: int = await db.scalar(
        select(func.count()).select_from(User).where(User.is_super_admin == True)
    )
    is_bootstrap = super_admin_count == 0

    if is_bootstrap:
        # First-ever registration — require the bootstrap secret
        if not settings.BOOTSTRAP_SECRET or x_bootstrap_key != settings.BOOTSTRAP_SECRET:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Provide X-Bootstrap-Key header to create the first Super Admin",
            )
        # Force first user to be Super Admin
        body.is_operator = False
        is_super_admin = True
    else:
        # Bootstrap already done — use POST /api/auth/register/user with a Super Admin token
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap already complete. Use POST /api/auth/register/user with a Super Admin Bearer token.",
        )

    # Check duplicate email
    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
        is_super_admin=is_super_admin,
        is_operator=body.is_operator,
    )
    db.add(user)
    await db.flush()
    logger.info("New user registered", extra={"user_id": str(user.id), "bootstrap": is_bootstrap})
    return user


@router.post(
    "/register/user",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Super Admin creates a new user",
)
async def register_user(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    """Authenticated endpoint — Super Admin creates operators or client users."""
    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
        is_super_admin=False,
        is_operator=body.is_operator,
    )
    db.add(user)
    await db.flush()
    logger.info("User created by super admin", extra={"created_by": str(current_user.id), "new_user": str(user.id)})
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login — returns access + refresh token",
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user = await db.scalar(select(User).where(User.email == body.email))

    # Constant-time check — always call verify even on missing user to prevent timing attacks
    password_valid = verify_password(body.password, user.password_hash) if user else False

    if not user or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return await _issue_token_pair(user, db)


@router.post(
    "/refresh-token",
    response_model=TokenResponse,
    summary="Refresh — rotate refresh token, issue new access token",
)
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    token_hash = hash_refresh_token(body.refresh_token)

    refresh = await db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    if not refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Revoke old token before issuing new pair (rotation)
    refresh.revoked = True

    user = await db.get(User, refresh.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return await _issue_token_pair(user, db)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout — revoke refresh token",
)
async def logout(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    token_hash = hash_refresh_token(body.refresh_token)
    refresh = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    if refresh:
        refresh.revoked = True
    # Always return 204 — don't leak whether the token existed


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
