from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CandidateProfile, Company
from app.db.session import get_db
from app.schemas.company import CompanyCreate
from app.services.company_import import import_companies
from app.services.company_store import upsert_company
from app.services.job_service import ingest_company_jobs
from app.services.pipeline_service import run_pipeline

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("/import")
async def import_company_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    filename = file.filename or ""
    if not filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Upload an Excel file (.xlsx or .xls).")

    try:
        result = import_companies(await file.read())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read the Excel file.") from exc

    stored = []
    ingestion = []
    for company_data in result.imported:
        company = upsert_company(db, company_data)
        db.commit()
        db.refresh(company)
        stored.append(company)
        try:
            jobs = await ingest_company_jobs(db, company)
            ingestion.append({
                "company_id": company.id,
                "company": company.name,
                "platform": company.platform,
                "jobs_ingested": len(jobs),
                "status": "completed",
            })
        except Exception as exc:
            # Keep the company even when its source cannot be scraped.
            db.rollback()
            ingestion.append({
                "company_id": company.id,
                "company": company.name,
                "platform": company.platform,
                "jobs_ingested": 0,
                "status": "failed",
                "error": str(exc)[:500],
            })

    candidate = db.scalar(select(CandidateProfile).order_by(CandidateProfile.id.desc()))
    pipeline_results = []
    pipeline_errors = []
    if candidate:
        jobs = db.scalars(
            select(__import__("app.db.models", fromlist=["Job"]).Job)
            .where(__import__("app.db.models", fromlist=["Job"]).Job.company_id.in_([c.id for c in stored]))
            .order_by(__import__("app.db.models", fromlist=["Job"]).Job.id)
        ).all()
        for job in jobs:
            try:
                pipeline_results.append(run_pipeline(db, candidate, job, use_llm=False).model_dump())
            except Exception as exc:
                pipeline_errors.append({
                    "job_id": job.id,
                    "title": job.title,
                    "error": str(exc)[:1000],
                })

    return {
        "imported": len(stored),
        "duplicates": len(result.duplicates),
        "invalid": len(result.invalid),
        "companies": [
            {"id": c.id, "name": c.name, "careers_url": c.careers_url, "platform": c.platform}
            for c in stored
        ],
        "ingestion": ingestion,
        "jobs_ingested": sum(item["jobs_ingested"] for item in ingestion),
        "pipeline": {
            "candidate_id": candidate.id if candidate else None,
            "processed": len(pipeline_results),
            "failed": len(pipeline_errors),
            "results": pipeline_results,
            "errors": pipeline_errors,
            "requires_candidate": candidate is None,
        },
        "duplicate_names": result.duplicates,
        "invalid_rows": result.invalid,
    }


@router.get("")
def list_companies(db: Session = Depends(get_db)):
    companies = db.scalars(select(Company).order_by(Company.name)).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "careers_url": c.careers_url,
            "platform": c.platform,
            "active": c.active,
        }
        for c in companies
    ]


@router.post("")
def create_company(data: CompanyCreate, db: Session = Depends(get_db)):
    company = upsert_company(db, data)
    db.commit()
    db.refresh(company)
    return {
        "id": company.id,
        "name": company.name,
        "careers_url": company.careers_url,
        "platform": company.platform,
    }
