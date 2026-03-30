"""
Tests for Client API — Operator-scoped.

Covers:
- Create / list / get / update client
- Status transitions (including guard: cannot revert to setup_pending)
- Soft-delete (suspend)
- Tenant isolation: operator cannot see clients of another tenant
"""

import pytest
from httpx import AsyncClient

from app.core.config import settings

BOOTSTRAP_KEY = settings.BOOTSTRAP_SECRET


async def _bootstrap(client: AsyncClient) -> tuple[dict, str]:
    """Create super admin; return (admin_headers, tenant_id)."""
    await client.post(
        f"{settings.API_PREFIX}/auth/register",
        json={"email": "admin@test.com", "password": "adminpass1"},
        headers={"X-Bootstrap-Key": BOOTSTRAP_KEY},
    )
    login_r = await client.post(
        f"{settings.API_PREFIX}/auth/login",
        json={"email": "admin@test.com", "password": "adminpass1"},
    )
    admin_headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}

    tenant_r = await client.post(
        f"{settings.API_PREFIX}/admin/tenants",
        json={"name": "Test Tenant"},
        headers=admin_headers,
    )
    tenant_id = tenant_r.json()["id"]
    return admin_headers, tenant_id


async def _make_operator(
    client: AsyncClient, admin_headers: dict, tenant_id: str, email: str = "op@test.com"
) -> dict:
    """Create an operator in the given tenant; return auth headers."""
    await client.post(
        f"{settings.API_PREFIX}/auth/register/user",
        json={
            "email": email,
            "password": "oppass12",
            "is_operator": True,
            "tenant_id": tenant_id,
        },
        headers=admin_headers,
    )
    login_r = await client.post(
        f"{settings.API_PREFIX}/auth/login",
        json={"email": email, "password": "oppass12"},
    )
    return {"Authorization": f"Bearer {login_r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_create_and_list_clients(client: AsyncClient):
    admin_h, tenant_id = await _bootstrap(client)
    op_h = await _make_operator(client, admin_h, tenant_id)

    # Create
    r = await client.post(
        f"{settings.API_PREFIX}/clients",
        json={"name": "Acme Client", "industry": "Finance", "team_size": 50},
        headers=op_h,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Acme Client"
    assert data["status"] == "setup_pending"
    assert data["tenant_id"] == tenant_id

    # List
    r = await client.get(f"{settings.API_PREFIX}/clients", headers=op_h)
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_get_client(client: AsyncClient):
    admin_h, tenant_id = await _bootstrap(client)
    op_h = await _make_operator(client, admin_h, tenant_id)

    create_r = await client.post(
        f"{settings.API_PREFIX}/clients",
        json={"name": "GetMe"},
        headers=op_h,
    )
    client_id = create_r.json()["id"]

    r = await client.get(f"{settings.API_PREFIX}/clients/{client_id}", headers=op_h)
    assert r.status_code == 200
    assert r.json()["id"] == client_id


@pytest.mark.asyncio
async def test_update_client(client: AsyncClient):
    admin_h, tenant_id = await _bootstrap(client)
    op_h = await _make_operator(client, admin_h, tenant_id)

    create_r = await client.post(
        f"{settings.API_PREFIX}/clients",
        json={"name": "Old Name"},
        headers=op_h,
    )
    client_id = create_r.json()["id"]

    r = await client.put(
        f"{settings.API_PREFIX}/clients/{client_id}",
        json={"name": "New Name", "team_size": 100},
        headers=op_h,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"
    assert r.json()["team_size"] == 100


@pytest.mark.asyncio
async def test_status_transition(client: AsyncClient):
    admin_h, tenant_id = await _bootstrap(client)
    op_h = await _make_operator(client, admin_h, tenant_id)

    create_r = await client.post(
        f"{settings.API_PREFIX}/clients",
        json={"name": "Status Client"},
        headers=op_h,
    )
    client_id = create_r.json()["id"]

    # setup_pending → active
    r = await client.put(
        f"{settings.API_PREFIX}/clients/{client_id}/status",
        json={"status": "active"},
        headers=op_h,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "active"

    # active → setup_pending: FORBIDDEN (409)
    r = await client.put(
        f"{settings.API_PREFIX}/clients/{client_id}/status",
        json={"status": "setup_pending"},
        headers=op_h,
    )
    assert r.status_code == 409

    # active → suspended
    r = await client.put(
        f"{settings.API_PREFIX}/clients/{client_id}/status",
        json={"status": "suspended"},
        headers=op_h,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "suspended"


@pytest.mark.asyncio
async def test_soft_delete_client(client: AsyncClient):
    admin_h, tenant_id = await _bootstrap(client)
    op_h = await _make_operator(client, admin_h, tenant_id)

    create_r = await client.post(
        f"{settings.API_PREFIX}/clients",
        json={"name": "DeleteMe"},
        headers=op_h,
    )
    client_id = create_r.json()["id"]

    r = await client.delete(
        f"{settings.API_PREFIX}/clients/{client_id}", headers=op_h
    )
    assert r.status_code == 204

    # Double suspend → 409
    r = await client.delete(
        f"{settings.API_PREFIX}/clients/{client_id}", headers=op_h
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_tenant_isolation(client: AsyncClient):
    """Operator A cannot see clients belonging to Operator B's tenant."""
    admin_h, tenant_a = await _bootstrap(client)

    # Second tenant
    tenant_b_r = await client.post(
        f"{settings.API_PREFIX}/admin/tenants",
        json={"name": "Tenant B"},
        headers=admin_h,
    )
    tenant_b = tenant_b_r.json()["id"]

    op_a = await _make_operator(client, admin_h, tenant_a, email="opa@test.com")
    op_b = await _make_operator(client, admin_h, tenant_b, email="opb@test.com")

    # Op B creates a client
    create_r = await client.post(
        f"{settings.API_PREFIX}/clients",
        json={"name": "Tenant B Client"},
        headers=op_b,
    )
    b_client_id = create_r.json()["id"]

    # Op A tries to access it → 404 (not 403)
    r = await client.get(
        f"{settings.API_PREFIX}/clients/{b_client_id}", headers=op_a
    )
    assert r.status_code == 404

    # Op A's list is empty
    r = await client.get(f"{settings.API_PREFIX}/clients", headers=op_a)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_invalid_status_value(client: AsyncClient):
    admin_h, tenant_id = await _bootstrap(client)
    op_h = await _make_operator(client, admin_h, tenant_id)

    create_r = await client.post(
        f"{settings.API_PREFIX}/clients",
        json={"name": "Validate Me"},
        headers=op_h,
    )
    client_id = create_r.json()["id"]

    r = await client.put(
        f"{settings.API_PREFIX}/clients/{client_id}/status",
        json={"status": "bogus"},
        headers=op_h,
    )
    assert r.status_code == 422
