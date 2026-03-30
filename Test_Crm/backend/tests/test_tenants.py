"""
Tests for Tenant API — Super Admin only.

Covers:
- Create tenant
- List tenants
- Get tenant by ID
- Update tenant name
- Suspend / activate tenant
- Access control (operator cannot access admin routes)
"""

import pytest
from httpx import AsyncClient

from app.core.config import settings

BOOTSTRAP_KEY = settings.BOOTSTRAP_SECRET


async def _create_super_admin(client: AsyncClient) -> dict:
    """Bootstrap the first super admin and return auth headers."""
    r = await client.post(
        f"{settings.API_PREFIX}/auth/register",
        json={"email": "admin@test.com", "password": "adminpass1"},
        headers={"X-Bootstrap-Key": BOOTSTRAP_KEY},
    )
    assert r.status_code == 201

    r = await client.post(
        f"{settings.API_PREFIX}/auth/login",
        json={"email": "admin@test.com", "password": "adminpass1"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_tenant(client: AsyncClient):
    headers = await _create_super_admin(client)
    r = await client.post(
        f"{settings.API_PREFIX}/admin/tenants",
        json={"name": "Acme Corp"},
        headers=headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Acme Corp"
    assert data["status"] == "active"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_tenants(client: AsyncClient):
    headers = await _create_super_admin(client)
    # Create two tenants
    for name in ("Tenant A", "Tenant B"):
        await client.post(
            f"{settings.API_PREFIX}/admin/tenants",
            json={"name": name},
            headers=headers,
        )

    r = await client.get(f"{settings.API_PREFIX}/admin/tenants", headers=headers)
    assert r.status_code == 200
    names = [t["name"] for t in r.json()]
    assert "Tenant A" in names
    assert "Tenant B" in names


@pytest.mark.asyncio
async def test_get_tenant(client: AsyncClient):
    headers = await _create_super_admin(client)
    create_r = await client.post(
        f"{settings.API_PREFIX}/admin/tenants",
        json={"name": "GetMe Corp"},
        headers=headers,
    )
    tenant_id = create_r.json()["id"]

    r = await client.get(f"{settings.API_PREFIX}/admin/tenants/{tenant_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["id"] == tenant_id


@pytest.mark.asyncio
async def test_update_tenant(client: AsyncClient):
    headers = await _create_super_admin(client)
    create_r = await client.post(
        f"{settings.API_PREFIX}/admin/tenants",
        json={"name": "Old Name"},
        headers=headers,
    )
    tenant_id = create_r.json()["id"]

    r = await client.put(
        f"{settings.API_PREFIX}/admin/tenants/{tenant_id}",
        json={"name": "New Name"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_suspend_and_activate_tenant(client: AsyncClient):
    headers = await _create_super_admin(client)
    create_r = await client.post(
        f"{settings.API_PREFIX}/admin/tenants",
        json={"name": "Toggle Corp"},
        headers=headers,
    )
    tenant_id = create_r.json()["id"]

    # Suspend
    r = await client.put(
        f"{settings.API_PREFIX}/admin/tenants/{tenant_id}/suspend",
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "suspended"

    # Double-suspend → 409
    r = await client.put(
        f"{settings.API_PREFIX}/admin/tenants/{tenant_id}/suspend",
        headers=headers,
    )
    assert r.status_code == 409

    # Activate
    r = await client.put(
        f"{settings.API_PREFIX}/admin/tenants/{tenant_id}/activate",
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "active"

    # Double-activate → 409
    r = await client.put(
        f"{settings.API_PREFIX}/admin/tenants/{tenant_id}/activate",
        headers=headers,
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_tenant_requires_super_admin(client: AsyncClient):
    """Operator cannot access admin tenant routes."""
    admin_headers = await _create_super_admin(client)

    # Create a tenant and an operator within it
    tenant_r = await client.post(
        f"{settings.API_PREFIX}/admin/tenants",
        json={"name": "Operator Tenant"},
        headers=admin_headers,
    )
    tenant_id = tenant_r.json()["id"]

    await client.post(
        f"{settings.API_PREFIX}/auth/register/user",
        json={
            "email": "op@test.com",
            "password": "oppass12",
            "is_operator": True,
            "tenant_id": tenant_id,
        },
        headers=admin_headers,
    )
    login_r = await client.post(
        f"{settings.API_PREFIX}/auth/login",
        json={"email": "op@test.com", "password": "oppass12"},
    )
    op_headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}

    r = await client.get(f"{settings.API_PREFIX}/admin/tenants", headers=op_headers)
    assert r.status_code == 403
