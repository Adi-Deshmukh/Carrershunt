from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Company
from app.db.session import get_db
from app.schemas.company import CompanyCreate
from app.services.company_import import import_companies
from app.services.company_store import upsert_company

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
    for company in result.imported:
        stored.append(upsert_company(db, company))
    db.commit()

    return {
        "imported": len(stored),
        "duplicates": len(result.duplicates),
        "invalid": len(result.invalid),
        "companies": [
            {"id": c.id, "name": c.name, "careers_url": c.careers_url, "platform": c.platform}
            for c in stored
        ],
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
