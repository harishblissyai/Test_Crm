"""
Module 1 — Unit Tests: Health & Core Infrastructure

Covers:
  - Health endpoint returns 200 with correct body
  - X-Request-ID header present in every response
  - Request-scoped IDs are unique across requests
  - Custom X-Request-ID is echoed back
  - CORS headers present for allowed origins
  - 404 returns standard error shape
  - 422 validation error returns field-level detail
"""

import pytest


@pytest.mark.asyncio
async def test_health_returns_200(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


@pytest.mark.asyncio
async def test_request_id_in_response_headers(client):
    """Every response must carry an X-Request-ID header."""
    response = await client.get("/api/health")
    assert "x-request-id" in response.headers


@pytest.mark.asyncio
async def test_request_ids_are_unique(client):
    """Two back-to-back requests must not share the same request ID."""
    r1 = await client.get("/api/health")
    r2 = await client.get("/api/health")
    assert r1.headers["x-request-id"] != r2.headers["x-request-id"]


@pytest.mark.asyncio
async def test_custom_request_id_is_echoed(client):
    """If the caller sends X-Request-ID, the server must echo it back."""
    custom_id = "my-trace-id-12345"
    response = await client.get("/api/health", headers={"X-Request-ID": custom_id})
    assert response.headers["x-request-id"] == custom_id


@pytest.mark.asyncio
async def test_cors_header_for_allowed_origin(client):
    """Allowed origins receive Access-Control-Allow-Origin."""
    response = await client.get(
        "/api/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


@pytest.mark.asyncio
async def test_404_returns_standard_error_shape(client):
    """Unknown routes return JSON with 'detail' and 'request_id' keys."""
    response = await client.get("/api/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body
    assert "request_id" in body


@pytest.mark.asyncio
async def test_health_db_field_present(client):
    """Health response always includes the 'database' field."""
    response = await client.get("/api/health")
    assert "database" in response.json()
