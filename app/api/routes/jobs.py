from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Company, Job
from app.db.session import get_db
from app.services.job_service import ingest_company_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/ingest/company/{company_id}")
async def ingest_jobs(company_id: int, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    jobs = await ingest_company_jobs(db, company)
    return {"company_id": company.id, "platform": company.platform, "jobs_ingested": len(jobs)}


@router.get("")
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.scalars(select(Job).order_by(Job.updated_at.desc())).all()
    return [
        {
            "id": j.id,
            "company_id": j.company_id,
            "title": j.title,
            "location": j.location,
            "employment_type": j.employment_type,
            "job_url": j.job_url,
            "source": j.source,
        }
        for j in jobs
    ]
