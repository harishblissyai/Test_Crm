"""
Client ORM model.

A Client is a customer/account managed by an Operator (tenant).
Each client gets its own isolated CRM workspace (contacts, tasks, config, etc.).
Status drives the lifecycle: setup_pending → active → suspended.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Every client belongs to exactly one tenant
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    industry: Mapped[str | None] = mapped_column(Text, nullable=True)
    team_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Lifecycle status
    # setup_pending → operator must complete onboarding wizard
    # active         → fully configured and in use
    # suspended      → temporarily disabled by operator or super admin
    status: Mapped[str] = mapped_column(
        String(20), default="setup_pending", nullable=False
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="clients")  # type: ignore[name-defined]
