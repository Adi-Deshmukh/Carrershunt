from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.models import CandidateProfile, Job, JobMatch
from app.db.session import get_db
from app.services.matching import match_job, serialize_match

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("/{job_id}")
def create_match(job_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    job = db.get(Job, job_id)
    candidate_query = select(CandidateProfile)
    if user.get("id"):
        candidate_query = candidate_query.where(CandidateProfile.supabase_user_id == user["id"])
    else:
        candidate_query = candidate_query.where(CandidateProfile.supabase_user_id.is_(None))
    candidate = db.scalar(candidate_query.order_by(CandidateProfile.id.desc()))
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
