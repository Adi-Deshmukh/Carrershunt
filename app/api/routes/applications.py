from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.models import Application, Job, UserApplication
from app.db.session import get_db

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("/{job_id}")
def create_application(
    job_id: int,
    status: str = "interested",
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    owner_id = user.get("id")
    if owner_id:
        existing = db.scalar(select(UserApplication).where(
            UserApplication.supabase_user_id == owner_id,
            UserApplication.job_id == job_id,
        ))
        if existing:
            existing.status = status
            existing.updated_at = datetime.utcnow()
            if status == "applied" and not existing.applied_at:
                existing.applied_at = datetime.utcnow()
            db.commit()
            return {"id": existing.id, "job_id": job_id, "status": existing.status}
        row = UserApplication(supabase_user_id=owner_id, job_id=job_id, status=status)
    else:
        existing = db.scalar(select(Application).where(Application.job_id == job_id))
        if existing:
            existing.status = status
            existing.updated_at = datetime.utcnow()
            if status == "applied" and not existing.applied_at:
                existing.applied_at = datetime.utcnow()
            db.commit()
            return {"id": existing.id, "job_id": job_id, "status": existing.status}
        row = Application(job_id=job_id, status=status)

    if status == "applied":
        row.applied_at = datetime.utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "job_id": job_id, "status": row.status}


@router.get("")
def list_applications(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    owner_id = user.get("id")
    if owner_id:
        rows = db.scalars(select(UserApplication).where(
            UserApplication.supabase_user_id == owner_id
        ).order_by(UserApplication.updated_at.desc())).all()
    else:
        rows = db.scalars(select(Application).order_by(Application.updated_at.desc())).all()
    return [
        {
            "id": row.id,
            "job_id": row.job_id,
            "status": row.status,
            "applied_at": row.applied_at,
            "updated_at": row.updated_at,
        }
        for row in rows
    ]


@router.patch("/{application_id}")
def update_application(
    application_id: int,
    status: str,
    notes: str | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    owner_id = user.get("id")
    if owner_id:
        row = db.scalar(select(UserApplication).where(
            UserApplication.id == application_id,
            UserApplication.supabase_user_id == owner_id,
        ))
    else:
        row = db.get(Application, application_id)
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")

    row.status = status
    row.notes = notes
    if status == "applied" and not row.applied_at:
        row.applied_at = datetime.utcnow()
    db.commit()
    return {"id": row.id, "status": row.status, "notes": row.notes}
