import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CandidateProfile, Job, OutreachMessage, Person
from app.db.session import get_db
from app.services.outreach_service import generate_outreach

router = APIRouter(prefix="/outreach", tags=["outreach"])


@router.post("/generate/{job_id}")
def create_outreach(job_id: int, person_id: int | None = None, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    candidate = db.scalar(select(CandidateProfile).order_by(CandidateProfile.id.desc()))
    person = db.get(Person, person_id) if person_id else None

    if not job or not candidate:
        raise HTTPException(status_code=404, detail="Job or candidate not found")

    draft = generate_outreach(candidate, job, person)
    message = OutreachMessage(
        job_id=job.id,
        person_id=person.id if person else None,
        channel="email" if candidate.email else "linkedin",
        subject=draft["subject"],
        body=draft["body"],
        status="draft",
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return {"id": message.id, **draft, "status": message.status}
