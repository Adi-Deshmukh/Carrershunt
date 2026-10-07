from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Company
from app.schemas.company import CompanyCreate


def upsert_company(db: Session, data: CompanyCreate) -> Company:
    existing = db.scalar(select(Company).where(Company.careers_url == str(data.careers_url)))
    if existing:
        existing.name = data.name
        return existing

    company = Company(name=data.name, careers_url=str(data.careers_url))
    db.add(company)
    db.flush()
    return company


def list_companies(db: Session) -> list[Company]:
    return list(db.scalars(select(Company).order_by(Company.name)))
