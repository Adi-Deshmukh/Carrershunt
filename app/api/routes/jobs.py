from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Company, IngestionRun, IngestionTask, Job
from app.db.session import get_db

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/ingest/company/{company_id}", status_code=202)
def ingest_jobs(company_id: int, db: Session = Depends(get_db)):
    """Queue a company crawl; the HTTP request never waits on the remote website."""
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    run = IngestionRun(total_companies=1, status="queued")
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
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.scalars(select(Job).order_by(Job.updated_at.desc())).all()
    return [
        {
            "id": j.id,
            "company_id": j.company_id,
            "title": j.title,
            "description": j.description,
            "location": j.location,
            "employment_type": j.employment_type,
            "job_url": j.job_url,
            "apply_url": j.apply_url or j.job_url,
            "source": j.source,
            "updated_at": j.updated_at,
            "company_name": j.company.name if j.company else None,
        }
        for j in jobs
    ]
