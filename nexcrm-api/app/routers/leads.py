import csv
import io
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.lead import LeadStatus
from app.models.user import User
from app.schemas.lead import LeadCreate, LeadUpdate, LeadStatusUpdate, LeadOut, LeadPage
from app.services import leads as svc

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=LeadPage)
def list_leads(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[LeadStatus] = Query(None),
    tag: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.list_leads(db, current_user.id, page, size, status, tag)


@router.post("", response_model=LeadOut, status_code=201)
def create_lead(
    data: LeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.create_lead(db, data, current_user.id)


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.get_lead(db, lead_id)


@router.put("/{lead_id}", response_model=LeadOut)
def update_lead(
    lead_id: int,
    data: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.update_lead(db, lead_id, data)


@router.patch("/{lead_id}/status", response_model=LeadOut)
def update_lead_status(
    lead_id: int,
    data: LeadStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.update_lead_status(db, lead_id, data.status)


@router.delete("/{lead_id}", status_code=204)
def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc.delete_lead(db, lead_id)


@router.get("/export/csv")
def export_leads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    leads = svc.get_all_leads(db)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "title", "status", "value", "notes", "created_at"])
    writer.writeheader()
    for l in leads:
        writer.writerow({
            "id": l.id, "title": l.title, "status": l.status.value,
            "value": l.value or "", "notes": l.notes or "",
            "created_at": l.created_at.isoformat(),
        })
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )
