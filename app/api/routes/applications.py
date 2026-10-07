from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Application, Job
from app.db.session import get_db

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("/{job_id}")
def create_application(job_id: int, status: str = "interested", db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    application = Application(job_id=job_id, status=status)
    if status == "applied":
        application.applied_at = datetime.utcnow()
    db.add(application)
    db.commit()
    db.refresh(application)
    return {"id": application.id, "job_id": job_id, "status": application.status}
