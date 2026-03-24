import math
from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.models.activity import Activity
from app.models.lead import Lead
from app.schemas.contact import ContactCreate, ContactUpdate


def list_contacts(db: Session, user_id: int, page: int, size: int, search: str | None, tag: str | None = None):
    q = db.query(Contact)
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                Contact.name.ilike(term),
                Contact.email.ilike(term),
                Contact.company.ilike(term),
            )
        )
    if tag:
        # JSON contains check — works for SQLite JSON arrays
        q = q.filter(Contact.tags.like(f'%"{tag}"%'))
    total = q.count()
    items = q.order_by(Contact.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {"items": items, "total": total, "page": page, "size": size, "pages": math.ceil(total / size) if total else 1}


def create_contact(db: Session, data: ContactCreate, user_id: int) -> Contact:
    contact = Contact(**data.model_dump(), created_by=user_id)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def get_contact(db: Session, contact_id: int) -> Contact:
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


def update_contact(db: Session, contact_id: int, data: ContactUpdate) -> Contact:
    contact = get_contact(db, contact_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return contact


def delete_contact(db: Session, contact_id: int) -> None:
    contact = get_contact(db, contact_id)
    db.delete(contact)
    db.commit()


def get_all_contacts(db: Session) -> list:
    return db.query(Contact).order_by(Contact.created_at.desc()).all()


def get_contact_timeline(db: Session, contact_id: int) -> list:
    get_contact(db, contact_id)  # 404 if not found

    events = []

    # Activities linked to this contact
    activities = db.query(Activity).filter(Activity.contact_id == contact_id).all()
    for a in activities:
        events.append({
            "id": f"activity-{a.id}",
            "kind": "activity",
            "subtype": a.type.value,
            "title": a.subject,
            "body": a.body,
            "lead_id": a.lead_id,
            "timestamp": a.created_at.isoformat(),
        })

    # Leads linked to this contact
    leads = db.query(Lead).filter(Lead.contact_id == contact_id).all()
    for l in leads:
        events.append({
            "id": f"lead-created-{l.id}",
            "kind": "lead",
            "subtype": "created",
            "title": f"Lead created: {l.title}",
            "body": f"Status: {l.status.value}" + (f" · Value: ${l.value:,.0f}" if l.value else ""),
            "lead_id": l.id,
            "timestamp": l.created_at.isoformat(),
        })
        if l.status.value in ("ClosedWon", "ClosedLost") and l.updated_at:
            events.append({
                "id": f"lead-closed-{l.id}",
                "kind": "lead",
                "subtype": l.status.value,
                "title": f"Lead {l.status.value.replace('Closed', 'Closed ').lower()}: {l.title}",
                "body": f"Value: ${l.value:,.0f}" if l.value else None,
                "lead_id": l.id,
                "timestamp": l.updated_at.isoformat(),
            })

    events.sort(key=lambda e: e["timestamp"], reverse=True)
    return events
