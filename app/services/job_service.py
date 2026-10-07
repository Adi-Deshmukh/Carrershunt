from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Company, Job
from app.services.job_sources.factory import detect_platform, get_source


async def ingest_company_jobs(db: Session, company: Company) -> list[Job]:
    platform = detect_platform(company.careers_url)
    company.platform = platform
    source = get_source(platform)
    records = await source.fetch_jobs(company.careers_url)

    stored: list[Job] = []
    for record in records:
        existing = db.scalar(select(Job).where(Job.job_url == record.job_url))
        if existing:
            existing.title = record.title
            existing.location = record.location
            existing.description = record.description
            existing.apply_url = record.apply_url
            existing.status = "open"
            stored.append(existing)
            continue

        job = Job(
            company_id=company.id,
            title=record.title,
            location=record.location,
            employment_type=record.employment_type,
            department=record.department,
            description=record.description,
            job_url=record.job_url,
            apply_url=record.apply_url,
            source=record.source,
            source_job_id=record.source_job_id,
        )
        db.add(job)
        stored.append(job)

    db.commit()
    return stored
