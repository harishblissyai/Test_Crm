import csv
import io
from typing import Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.contact import ContactCreate, ContactUpdate, ContactOut, ContactPage
from app.services import contacts as svc

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=ContactPage)
def list_contacts(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.list_contacts(db, current_user.id, page, size, search, tag)


@router.post("", response_model=ContactOut, status_code=201)
def create_contact(
    data: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.create_contact(db, data, current_user.id)


@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.get_contact(db, contact_id)


@router.put("/{contact_id}", response_model=ContactOut)
def update_contact(
    contact_id: int,
    data: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.update_contact(db, contact_id, data)


@router.delete("/{contact_id}", status_code=204)
def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc.delete_contact(db, contact_id)


@router.get("/{contact_id}/timeline")
def get_contact_timeline(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.get_contact_timeline(db, contact_id)


@router.get("/export/csv")
def export_contacts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contacts = svc.get_all_contacts(db)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "name", "email", "phone", "company", "notes", "created_at"])
    writer.writeheader()
    for c in contacts:
        writer.writerow({
            "id": c.id, "name": c.name, "email": c.email or "",
            "phone": c.phone or "", "company": c.company or "",
            "notes": c.notes or "", "created_at": c.created_at.isoformat(),
        })
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=contacts.csv"},
    )


@router.post("/import/csv")
async def import_contacts(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    imported, errors = 0, []
    for i, row in enumerate(reader, start=2):
        name = (row.get("name") or row.get("Name") or "").strip()
        if not name:
            errors.append(f"Row {i}: missing name")
            continue
        data = ContactCreate(
            name=name,
            email=(row.get("email") or row.get("Email") or "").strip() or None,
            phone=(row.get("phone") or row.get("Phone") or "").strip() or None,
            company=(row.get("company") or row.get("Company") or "").strip() or None,
            notes=(row.get("notes") or row.get("Notes") or "").strip() or None,
        )
        svc.create_contact(db, data, current_user.id)
        imported += 1
    return {"imported": imported, "errors": errors}
