import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.models import CandidateProfile, Job, PipelineRun
from app.db.session import get_db
from app.services.pipeline_service import run_pipeline

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


def _candidate_for_user(db: Session, user: dict, candidate_id: int | None = None) -> CandidateProfile | None:
    statement = select(CandidateProfile)
    if user.get("id"):
        statement = statement.where(CandidateProfile.supabase_user_id == user["id"])
    else:
        statement = statement.where(CandidateProfile.supabase_user_id.is_(None))
    if candidate_id is not None:
        statement = statement.where(CandidateProfile.id == candidate_id)
    return db.scalar(statement.order_by(CandidateProfile.id.desc()))


@router.post("/{job_id}")
def execute_pipeline(
    job_id: int,
    candidate_id: int | None = None,
    use_llm: bool = False,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    job = db.get(Job, job_id)
    candidate = _candidate_for_user(db, user, candidate_id)
    if not job or not candidate:
        raise HTTPException(status_code=404, detail="Job or your candidate profile was not found")
    if not (job.description or "").strip() or len(job.description.strip()) < 100:
        raise HTTPException(status_code=422, detail="This posting has no usable job description. Re-ingest the company source before analysis.")
    return run_pipeline(db, candidate, job, use_llm=use_llm).model_dump()


@router.get("/jobs/{job_id}/latest")
def get_latest_job_run(
    job_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    candidate = _candidate_for_user(db, user)
    if not candidate:
        raise HTTPException(status_code=404, detail="Create your candidate profile before analyzing jobs.")
    run = db.scalar(
        select(PipelineRun)
        .where(PipelineRun.job_id == job_id, PipelineRun.candidate_id == candidate.id)
        .order_by(PipelineRun.id.desc())
    )
    if not run:
        raise HTTPException(status_code=404, detail="No analysis exists for this role yet.")
    return {
        "id": run.id,
        "candidate_id": run.candidate_id,
        "job_id": run.job_id,
        "status": run.status,
        "result": None if not run.result_json else json.loads(run.result_json),
        "error": run.error,
    }


@router.get("/runs/{run_id}")
def get_pipeline_run(
    run_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    candidate = _candidate_for_user(db, user)
    run = db.get(PipelineRun, run_id)
    if not candidate or not run or run.candidate_id != candidate.id:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return {
        "id": run.id,
        "candidate_id": run.candidate_id,
        "job_id": run.job_id,
        "status": run.status,
        "result": None if not run.result_json else json.loads(run.result_json),
        "error": run.error,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
    }
