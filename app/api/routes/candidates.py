import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CandidateProfile
from app.db.session import get_db
from app.schemas.candidate import CandidateCreate

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("")
def create_candidate(data: CandidateCreate, db: Session = Depends(get_db)):
    candidate = CandidateProfile(
        name=data.name,
        email=data.email,
        education=data.education,
        graduation_year=data.graduation_year,
        experience_years=data.experience_years,
        location=data.location,
        work_authorization=data.work_authorization,
        resume_text=data.resume_text,
        evidence_json=json.dumps(data.evidence),
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return {"id": candidate.id, "name": candidate.name}


@router.get("/latest")
def get_latest_candidate(db: Session = Depends(get_db)):
    candidate = db.scalar(select(CandidateProfile).order_by(CandidateProfile.id.desc()))
    if not candidate:
        return None
    return {
        "id": candidate.id,
        "name": candidate.name,
        "email": candidate.email,
        "education": candidate.education,
        "graduation_year": candidate.graduation_year,
        "experience_years": candidate.experience_years,
        "location": candidate.location,
        "work_authorization": candidate.work_authorization,
        "resume_text": candidate.resume_text,
        "evidence": json.loads(candidate.evidence_json or "{}"),
    }
