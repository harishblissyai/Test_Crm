from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.models.lead import LeadStatus


class LeadCreate(BaseModel):
    title: str
    contact_id: Optional[int] = None
    status: LeadStatus = LeadStatus.New
    value: Optional[float] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = []


class LeadUpdate(BaseModel):
    title: Optional[str] = None
    contact_id: Optional[int] = None
    status: Optional[LeadStatus] = None
    value: Optional[float] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = None


class LeadStatusUpdate(BaseModel):
    status: LeadStatus


class LeadOut(BaseModel):
    id: int
    title: str
    contact_id: Optional[int] = None
    status: LeadStatus
    value: Optional[float] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = []
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LeadPage(BaseModel):
    items: list[LeadOut]
    total: int
    page: int
    size: int
    pages: int
