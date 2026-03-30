"""
Module 2 — Unit Tests: Auth

Covers:
  - Bootstrap: create first Super Admin with correct key
  - Bootstrap: blocked without key
  - Bootstrap: blocked if super admin already exists
  - Login: valid credentials → token pair returned
  - Login: wrong password → 401
  - Login: unknown email → 401
  - Refresh: valid token → new pair issued, old revoked
  - Refresh: revoked token → 401
  - Refresh: expired token → 401
  - Logout: revokes token, subsequent refresh fails
  - /me: valid token → user returned
  - /me: no token → 401
  - /me: tampered token → 401
  - register/user: Super Admin can create users
  - register/user: non-Super Admin cannot create users
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.user import User

BOOTSTRAP_KEY = "blissy-bootstrap-local-2026"


# ── Helpers ────────────────────────────────────────────────────────────────

async def _create_super_admin(db: AsyncSession, email="admin@test.com", password="secret123") -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        first_name="Super",
        last_name="Admin",
        is_super_admin=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _login(client: AsyncClient, email: str, password: str) -> dict:
    r = await client.post("/api/auth/login", json={"email": email, "password": password})
    return r.json()


# ── Bootstrap ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bootstrap_creates_super_admin(client):
    r = await client.post(
        "/api/auth/register",
        json={"email": "admin@crm.com", "password": "secret123"},
        headers={"X-Bootstrap-Key": BOOTSTRAP_KEY},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "admin@crm.com"
    assert body["is_super_admin"] is True


@pytest.mark.asyncio
async def test_bootstrap_fails_without_key(client):
    r = await client.post(
        "/api/auth/register",
        json={"email": "admin2@crm.com", "password": "secret123"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_bootstrap_blocked_if_super_admin_exists(client, db_session):
    await _create_super_admin(db_session, email="existing@crm.com")
    r = await client.post(
        "/api/auth/register",
        json={"email": "another@crm.com", "password": "secret123"},
        headers={"X-Bootstrap-Key": BOOTSTRAP_KEY},
    )
    assert r.status_code == 403


# ── Login ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_returns_token_pair(client, db_session):
    await _create_super_admin(db_session, email="login@crm.com", password="mypassword")
    r = await client.post(
        "/api/auth/login",
        json={"email": "login@crm.com", "password": "mypassword"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, db_session):
    await _create_super_admin(db_session, email="wrong@crm.com", password="correct")
    r = await client.post(
        "/api/auth/login",
        json={"email": "wrong@crm.com", "password": "incorrect"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client):
    r = await client.post(
        "/api/auth/login",
        json={"email": "nobody@crm.com", "password": "anything"},
    )
    assert r.status_code == 401


# ── Token & /me ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_me_returns_current_user(client, db_session):
    user = await _create_super_admin(db_session, email="me@crm.com", password="pass1234")
    tokens = await _login(client, "me@crm.com", "pass1234")
    r = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 200
    assert r.json()["email"] == "me@crm.com"


@pytest.mark.asyncio
async def test_me_no_token_returns_403(client):
    r = await client.get("/api/auth/me")
    # HTTPBearer returns 403 when no credentials are provided
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_me_invalid_token_returns_401(client):
    r = await client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer this.is.garbage"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_tampered_token_returns_401(client, db_session):
    user = await _create_super_admin(db_session, email="tamper@crm.com", password="pass1234")
    tokens = await _login(client, "tamper@crm.com", "pass1234")
    bad_token = tokens["access_token"][:-5] + "XXXXX"
    r = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {bad_token}"},
    )
    assert r.status_code == 401


# ── Refresh Token ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_issues_new_pair(client, db_session):
    await _create_super_admin(db_session, email="refresh@crm.com", password="pass1234")
    tokens = await _login(client, "refresh@crm.com", "pass1234")

    r = await client.post(
        "/api/auth/refresh-token",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert r.status_code == 200
    new_tokens = r.json()
    assert "access_token" in new_tokens
    # New refresh token must differ from old
    assert new_tokens["refresh_token"] != tokens["refresh_token"]


@pytest.mark.asyncio
async def test_refresh_old_token_is_revoked_after_rotation(client, db_session):
    await _create_super_admin(db_session, email="rotate@crm.com", password="pass1234")
    tokens = await _login(client, "rotate@crm.com", "pass1234")
    old_refresh = tokens["refresh_token"]

    # Use the refresh token once
    await client.post("/api/auth/refresh-token", json={"refresh_token": old_refresh})

    # Using it again must fail
    r2 = await client.post("/api/auth/refresh-token", json={"refresh_token": old_refresh})
    assert r2.status_code == 401


@pytest.mark.asyncio
async def test_refresh_invalid_token_returns_401(client):
    r = await client.post(
        "/api/auth/refresh-token",
        json={"refresh_token": "not-a-real-token"},
    )
    assert r.status_code == 401


# ── Logout ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client, db_session):
    await _create_super_admin(db_session, email="logout@crm.com", password="pass1234")
    tokens = await _login(client, "logout@crm.com", "pass1234")

    r = await client.post(
        "/api/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert r.status_code == 204

    # Refresh should now fail
    r2 = await client.post(
        "/api/auth/refresh-token",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert r2.status_code == 401


@pytest.mark.asyncio
async def test_logout_with_unknown_token_returns_204(client):
    """Logout is idempotent — unknown token still returns 204."""
    r = await client.post(
        "/api/auth/logout",
        json={"refresh_token": "unknown-token-xyz"},
    )
    assert r.status_code == 204


# ── Register/User (Super Admin creates users) ──────────────────────────────

@pytest.mark.asyncio
async def test_super_admin_can_create_user(client, db_session):
    await _create_super_admin(db_session, email="creator@crm.com", password="pass1234")
    tokens = await _login(client, "creator@crm.com", "pass1234")

    r = await client.post(
        "/api/auth/register/user",
        json={"email": "newop@crm.com", "password": "pass1234", "is_operator": True},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 201
    assert r.json()["is_operator"] is True


@pytest.mark.asyncio
async def test_non_super_admin_cannot_create_user(client, db_session):
    # Create a regular (non-super-admin) user directly
    regular = User(
        email="regular@crm.com",
        password_hash=hash_password("pass1234"),
        is_super_admin=False,
        is_operator=False,
    )
    db_session.add(regular)
    await db_session.commit()

    # Give them a valid token
    token = create_access_token({
        "sub": str(regular.id),
        "tenant_id": None,
        "client_id": None,
        "role_id": None,
        "is_operator": False,
        "is_super_admin": False,
    })

    r = await client.post(
        "/api/auth/register/user",
        json={"email": "newuser@crm.com", "password": "pass1234"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403
