from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import Company
from app.db.session import get_db
from app.services.job_service import ingest_company_jobs

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("/company/{company_id}")
async def scan_company(company_id: int, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if not company:
        return {"error": "Company not found"}

    jobs = await ingest_company_jobs(db, company)
    return {
        "company": company.name,
        "platform": company.platform,
        "jobs_found": len(jobs),
        "jobs": [{"id": j.id, "title": j.title, "url": j.job_url} for j in jobs],
    }
