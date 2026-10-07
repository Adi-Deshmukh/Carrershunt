from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CandidateProfile, Job, JobMatch
from app.db.session import get_db
from app.services.matching import match_job, serialize_match

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("/{job_id}")
def create_match(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    candidate = db.scalar(select(CandidateProfile).order_by(CandidateProfile.id.desc()))
    if not job or not candidate:
        raise HTTPException(status_code=404, detail="Job or candidate profile not found")

    result = match_job(job, candidate)
    gaps, evidence = serialize_match(result)

    record = JobMatch(
        job_id=job.id,
        fit_score=result.fit_score,
        interview_estimate=result.interview_estimate,
        confidence=result.confidence,
        eligible=result.eligible,
        explanation=result.explanation,
        gaps_json=gaps,
        evidence_json=evidence,
    )
    db.add(record)
    db.commit()
    return result.model_dump()
