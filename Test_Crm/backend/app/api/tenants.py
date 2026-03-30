"""
Tenant API — Super Admin only.

Tenants are the top-level entity (Brands / Agencies).
Only Super Admins can create, update, and suspend tenants.

Routes:
    GET    /api/admin/tenants
    POST   /api/admin/tenants
    GET    /api/admin/tenants/{tenant_id}
    PUT    /api/admin/tenants/{tenant_id}
    PUT    /api/admin/tenants/{tenant_id}/suspend
    PUT    /api/admin/tenants/{tenant_id}/activate
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_super_admin
from app.db.session import get_db
from app.models.user import Tenant, User
from app.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate

router = APIRouter(prefix="/admin/tenants", tags=["Tenants (Admin)"])
logger = logging.getLogger(__name__)


async def _get_tenant_or_404(tenant_id: uuid.UUID, db: AsyncSession) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


@router.get("", response_model=list[TenantResponse], summary="List all tenants")
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> list[Tenant]:
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    return list(result.scalars().all())


@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tenant (Brand/Agency)",
)
async def create_tenant(
    body: TenantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> Tenant:
    tenant = Tenant(name=body.name)
    db.add(tenant)
    await db.flush()
    logger.info("Tenant created", extra={"tenant_id": str(tenant.id), "by": str(current_user.id)})
    return tenant


@router.get("/{tenant_id}", response_model=TenantResponse, summary="Get a tenant by ID")
async def get_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> Tenant:
    return await _get_tenant_or_404(tenant_id, db)


@router.put("/{tenant_id}", response_model=TenantResponse, summary="Update tenant name")
async def update_tenant(
    tenant_id: uuid.UUID,
    body: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> Tenant:
    tenant = await _get_tenant_or_404(tenant_id, db)
    if body.name is not None:
        tenant.name = body.name
    return tenant


@router.put(
    "/{tenant_id}/suspend",
    response_model=TenantResponse,
    summary="Suspend a tenant — disables all access for their users",
)
async def suspend_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> Tenant:
    tenant = await _get_tenant_or_404(tenant_id, db)
    if tenant.status == "suspended":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Tenant is already suspended"
        )
    tenant.status = "suspended"
    logger.info("Tenant suspended", extra={"tenant_id": str(tenant_id)})
    return tenant


@router.put(
    "/{tenant_id}/activate",
    response_model=TenantResponse,
    summary="Reactivate a suspended tenant",
)
async def activate_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> Tenant:
    tenant = await _get_tenant_or_404(tenant_id, db)
    if tenant.status == "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Tenant is already active"
        )
    tenant.status = "active"
    logger.info("Tenant activated", extra={"tenant_id": str(tenant_id)})
    return tenant
