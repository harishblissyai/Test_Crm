import math
from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.lead import Lead, LeadStatus
from app.schemas.lead import LeadCreate, LeadUpdate


def list_leads(db: Session, user_id: int, page: int, size: int, status: LeadStatus | None, tag: str | None = None):
    q = db.query(Lead)
    if status:
        q = q.filter(Lead.status == status)
    if tag:
        q = q.filter(Lead.tags.like(f'%"{tag}"%'))
    total = q.count()
    items = q.order_by(Lead.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {"items": items, "total": total, "page": page, "size": size, "pages": math.ceil(total / size) if total else 1}


def create_lead(db: Session, data: LeadCreate, user_id: int) -> Lead:
    lead = Lead(**data.model_dump(), created_by=user_id)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def get_lead(db: Session, lead_id: int) -> Lead:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


def update_lead(db: Session, lead_id: int, data: LeadUpdate) -> Lead:
    lead = get_lead(db, lead_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    db.commit()
    db.refresh(lead)
    return lead


def update_lead_status(db: Session, lead_id: int, status: LeadStatus) -> Lead:
    lead = get_lead(db, lead_id)
    lead.status = status
    db.commit()
    db.refresh(lead)
    return lead


def delete_lead(db: Session, lead_id: int) -> None:
    lead = get_lead(db, lead_id)
    db.delete(lead)
    db.commit()


def get_all_leads(db: Session) -> list:
    return db.query(Lead).order_by(Lead.created_at.desc()).all()


def search_leads(db: Session, term: str) -> list[Lead]:
    t = f"%{term}%"
    return db.query(Lead).filter(
        or_(Lead.title.ilike(t), Lead.notes.ilike(t))
    ).limit(20).all()
