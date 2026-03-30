"""
Client API — Operator-scoped.

Clients are accounts/customers managed by an Operator under a Tenant.
Every query is filtered by tenant_id — operators can only see their own clients.

Routes:
    GET    /api/clients                    — list clients in operator's tenant
    POST   /api/clients                    — create a new client
    GET    /api/clients/{client_id}        — get client detail
    PUT    /api/clients/{client_id}        — update client info
    PUT    /api/clients/{client_id}/status — change client status
    DELETE /api/clients/{client_id}        — suspend client (soft delete)
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_operator, require_tenant_context, verify_client_access
from app.db.session import get_db
from app.models.client import Client
from app.models.user import User
from app.schemas.client import (
    ClientCreate,
    ClientResponse,
    ClientStatusUpdate,
    ClientUpdate,
)

router = APIRouter(prefix="/clients", tags=["Clients"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[ClientResponse], summary="List all clients in your tenant")
async def list_clients(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(require_tenant_context),
) -> list[Client]:
    result = await db.execute(
        select(Client)
        .where(Client.tenant_id == tenant_id)
        .order_by(Client.created_at.desc())
    )
    return list(result.scalars().all())


@router.post(
    "",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new client under your tenant",
)
async def create_client(
    body: ClientCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
    tenant_id: uuid.UUID = Depends(require_tenant_context),
) -> Client:
    client = Client(
        tenant_id=tenant_id,
        name=body.name,
        industry=body.industry,
        team_size=body.team_size,
        created_by=user.id,
    )
    db.add(client)
    await db.flush()
    logger.info(
        "Client created",
        extra={"client_id": str(client.id), "tenant_id": str(tenant_id), "by": str(user.id)},
    )
    return client


@router.get(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Get client detail",
)
async def get_client(
    client: Client = Depends(verify_client_access),
) -> Client:
    return client


@router.put(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Update client name, industry, or team size",
)
async def update_client(
    body: ClientUpdate,
    client: Client = Depends(verify_client_access),
) -> Client:
    if body.name is not None:
        client.name = body.name
    if body.industry is not None:
        client.industry = body.industry
    if body.team_size is not None:
        client.team_size = body.team_size
    return client


@router.put(
    "/{client_id}/status",
    response_model=ClientResponse,
    summary="Change client status (setup_pending → active → suspended)",
)
async def update_client_status(
    body: ClientStatusUpdate,
    client: Client = Depends(verify_client_access),
    _: User = Depends(require_operator),
) -> Client:
    # Guard: cannot go backwards from active to setup_pending
    if body.status == "setup_pending" and client.status != "setup_pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot revert a client to setup_pending once configuration is started",
        )
    client.status = body.status
    logger.info(
        "Client status changed",
        extra={"client_id": str(client.id), "new_status": body.status},
    )
    return client


@router.delete(
    "/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Suspend a client (soft delete — data is preserved)",
)
async def suspend_client(
    client: Client = Depends(verify_client_access),
    _: User = Depends(require_operator),
) -> None:
    if client.status == "suspended":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Client is already suspended"
        )
    client.status = "suspended"
    logger.info("Client suspended", extra={"client_id": str(client.id)})
