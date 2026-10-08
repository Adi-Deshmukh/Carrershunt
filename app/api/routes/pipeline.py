from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CandidateProfile, Job, PipelineRun
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


@router.get("/jobs/{job_id}/latest")
def get_latest_job_run(job_id: int, db: Session = Depends(get_db)):
    run = db.scalar(select(PipelineRun).where(PipelineRun.job_id == job_id).order_by(PipelineRun.id.desc()))
    if not run:
        raise HTTPException(status_code=404, detail="No pipeline run for this job")
    return {
        "id": run.id,
        "candidate_id": run.candidate_id,
        "job_id": run.job_id,
        "status": run.status,
        "result": None if not run.result_json else __import__("json").loads(run.result_json),
        "error": run.error,
    }


@router.get("/runs/{run_id}")
def get_pipeline_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(PipelineRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return {
        "id": run.id,
        "candidate_id": run.candidate_id,
        "job_id": run.job_id,
        "status": run.status,
        "result": None if not run.result_json else __import__("json").loads(run.result_json),
        "error": run.error,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
    }
