from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CandidateProfile, Job
from app.db.session import get_db
from app.services.pipeline_service import run_pipeline

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/{job_id}")
def execute_pipeline(
    job_id: int,
    candidate_id: int | None = None,
    use_llm: bool = False,
    db: Session = Depends(get_db),
):
    job = db.get(Job, job_id)
    candidate = db.get(CandidateProfile, candidate_id) if candidate_id else db.scalar(
        select(CandidateProfile).order_by(CandidateProfile.id.desc())
    )
    if not job or not candidate:
        raise HTTPException(status_code=404, detail="Job or candidate profile not found")
    return run_pipeline(db, candidate, job, use_llm=use_llm).model_dump()
