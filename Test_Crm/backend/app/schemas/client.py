"""Pydantic schemas for Client endpoints (Operator-scoped)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

# Valid status values and allowed transitions
CLIENT_STATUSES = {"setup_pending", "active", "suspended"}


class ClientCreate(BaseModel):
    name: str
    industry: str | None = None
    team_size: int | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Client name cannot be empty")
        return v.strip()

    @field_validator("team_size")
    @classmethod
    def team_size_positive(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("Team size must be at least 1")
        return v


class ClientUpdate(BaseModel):
    name: str | None = None
    industry: str | None = None
    team_size: int | None = None


class ClientStatusUpdate(BaseModel):
    """Used by operator/admin to change a client's status."""
    status: str

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        if v not in CLIENT_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(CLIENT_STATUSES)}")
        return v


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    industry: str | None
    team_size: int | None
    status: str
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
