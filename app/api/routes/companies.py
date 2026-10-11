from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CandidateProfile, Company, IngestionRun, IngestionTask
from app.db.session import get_db
from app.schemas.company import CompanyCreate
from app.services.company_import import import_companies
from app.services.company_store import upsert_company

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("/import", status_code=202)
async def import_company_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    """Persist companies and enqueue scraping; never scrape inside the upload request."""
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
    for company_data in result.imported:
        company = upsert_company(db, company_data)
        db.commit()
        db.refresh(company)
        stored.append(company)

    run = IngestionRun(total_companies=len(stored), status="queued" if stored else "completed")
    db.add(run)
    db.flush()
    for company in stored:
        db.add(
            IngestionTask(
                run_id=run.id,
                task_type="scrape_company",
                company_id=company.id,
                status="queued",
            )
        )
    db.commit()
    db.refresh(run)

    candidate_exists = db.scalar(
        select(CandidateProfile.id).order_by(CandidateProfile.id.desc()).limit(1)
    ) is not None
    return {
        "imported": len(stored),
        "duplicates": len(result.duplicates),
        "invalid": len(result.invalid),
        "companies": [
            {"id": company.id, "name": company.name, "careers_url": company.careers_url, "platform": company.platform}
            for company in stored
        ],
        "ingestion_run_id": run.id,
        "status": run.status,
        "queued_companies": len(stored),
        "jobs_ingested": 0,
        "pipeline": {
            "candidate_id": None,
            "processed": 0,
            "failed": 0,
            "results": [],
            "errors": [],
            "requires_candidate": not candidate_exists,
        },
        "duplicate_names": result.duplicates,
        "invalid_rows": result.invalid,
    }


@router.get("/import-runs/latest")
def get_latest_import_run(db: Session = Depends(get_db)) -> dict:
    run = db.scalar(select(IngestionRun).order_by(IngestionRun.id.desc()))
    if run is None:
        raise HTTPException(status_code=404, detail="No ingestion runs found")
    return get_import_run(run.id, db)


@router.get("/import-runs/{run_id}")
def get_import_run(run_id: int, db: Session = Depends(get_db)) -> dict:
    run = db.get(IngestionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Ingestion run not found")
    tasks = db.scalars(
        select(IngestionTask).where(IngestionTask.run_id == run_id).order_by(IngestionTask.id)
    ).all()
    counts = {state: sum(task.status == state for task in tasks) for state in ("queued", "running", "completed", "completed_with_warnings", "failed", "skipped")}
    return {
        "run_id": run.id,
        "status": run.status,
        "total_companies": run.total_companies,
        "task_counts": counts,
        "jobs_ingested": sum(task.jobs_ingested for task in tasks if task.task_type == "scrape_company"),
        "tasks": [
            {
                "id": task.id,
                "type": task.task_type,
                "company_id": task.company_id,
                "company": task.company.name if task.company else None,
                "job_id": task.job_id,
                "status": task.status,
                "attempts": task.attempts,
                "jobs_ingested": task.jobs_ingested,
                "worker_id": task.worker_id,
                "error": task.error,
            }
            for task in tasks
        ],
        "created_at": run.created_at,
        "updated_at": run.updated_at,
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
