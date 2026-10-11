from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.models import Company, IngestionRun, IngestionTask, Job
from app.db.session import get_db
from app.services.job_sources.generic import _looks_like_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _company_visible_to_user(db: Session, company_id: int, user: dict) -> bool:
    query = (
        select(IngestionTask.id)
        .join(IngestionRun, IngestionTask.run_id == IngestionRun.id)
        .where(IngestionTask.company_id == company_id)
    )
    if user.get("id"):
        query = query.where(IngestionRun.supabase_user_id == user["id"])
    else:
        query = query.where(IngestionRun.supabase_user_id.is_(None))
    return db.scalar(query.limit(1)) is not None


@router.post("/ingest/company/{company_id}", status_code=202)
def ingest_jobs(company_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Queue a company crawl only when it belongs to the current workspace."""
    company = db.get(Company, company_id)
    if not company or not _company_visible_to_user(db, company_id, user):
        raise HTTPException(status_code=404, detail="Company not found in your workspace")

    run = IngestionRun(total_companies=1, status="queued", supabase_user_id=user.get("id"))
    db.add(run)
    db.flush()
    db.add(IngestionTask(run_id=run.id, task_type="scrape_company", company_id=company.id, status="queued"))
    db.commit()
    db.refresh(run)
    return {
        "company_id": company.id,
        "ingestion_run_id": run.id,
        "platform": company.platform,
        "status": "queued",
        "queued_companies": 1,
    }


@router.get("")
def list_jobs(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    query = (
        select(Job)
        .join(Company, Job.company_id == Company.id)
        .join(IngestionTask, IngestionTask.company_id == Company.id)
        .join(IngestionRun, IngestionTask.run_id == IngestionRun.id)
        .where(Job.status == "open")
    )
    if user.get("id"):
        query = query.where(IngestionRun.supabase_user_id == user["id"])
    else:
        query = query.where(IngestionRun.supabase_user_id.is_(None))
    jobs = db.scalars(query.distinct().order_by(Job.updated_at.desc())).all()
    # Hide legacy generic-source rows that were collected from informational
    # pages before strict URL validation was introduced.
    jobs = [
        job for job in jobs
        if job.source != "generic" or _looks_like_job(job.title, job.job_url)
    ]
    return [
        {
            "id": job.id,
            "company_id": job.company_id,
            "title": job.title,
            "description": job.description,
            "location": job.location,
            "employment_type": job.employment_type,
            "job_url": job.job_url,
            "apply_url": job.apply_url or job.job_url,
            "source": job.source,
            "updated_at": job.updated_at,
            "company_name": job.company.name if job.company else None,
        }
        for job in jobs
    ]
