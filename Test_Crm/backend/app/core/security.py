"""
Security utilities — JWT creation/decoding and password hashing.

Everything in this file is a pure function (no DB, no FastAPI).
Easy to unit test in isolation.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# ── Password hashing ───────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── Access token (JWT) ─────────────────────────────────────────────────────

def create_access_token(payload: dict) -> str:
    """
    Signs a JWT access token.
    Caller provides the claims; this function adds exp and type.

    Expected payload keys:
        sub          — user UUID (string)
        tenant_id    — tenant UUID or None
        client_id    — client UUID or None
        role_id      — role string or None
        is_operator  — bool
        is_super_admin — bool
    """
    data = payload.copy()
    data["exp"] = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    data["type"] = "access"
    return jwt.encode(data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decodes and validates a JWT access token.
    Raises jose.JWTError on invalid/expired token.
    """
    payload = jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    if payload.get("type") != "access":
        raise JWTError("Not an access token")
    return payload


# ── Refresh token ──────────────────────────────────────────────────────────

def create_refresh_token() -> tuple[str, str]:
    """
    Generates a secure random refresh token.
    Returns (raw_token, sha256_hash).
    - Send raw_token to the client.
    - Store only the hash in the DB.
    """
    raw = secrets.token_urlsafe(32)
    hashed = _hash_refresh_token(raw)
    return raw, hashed


def _hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def hash_refresh_token(raw: str) -> str:
    """Public helper — hash an incoming refresh token for DB lookup."""
    return _hash_refresh_token(raw)
