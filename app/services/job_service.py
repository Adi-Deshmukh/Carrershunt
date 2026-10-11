from urllib.parse import urlparse

from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Company, Job
from app.services.job_sources.factory import detect_platform, get_source


def _clean_description(value: str | None) -> str:
    return " ".join(BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True).split())[:20000]


def _valid_public_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and not parsed.username and not parsed.password


async def ingest_company_jobs(db: Session, company: Company) -> list[Job]:
    platform = detect_platform(company.careers_url)
    company.platform = platform
    source = get_source(platform)
    records = await source.fetch_jobs(company.careers_url)

    # Do not persist placeholder rows, empty URLs, or a careers index masquerading
    # as an individual job. The pipeline must analyze a real posting page.
    valid_records = []
    for record in records:
        if not record.title or not _valid_public_url(record.job_url):
            continue
        if record.job_url.rstrip("/") == company.careers_url.rstrip("/"):
            continue
        description = _clean_description(record.description)
        if len(description) < 100:
            continue
        record.description = description
        if not _valid_public_url(record.apply_url):
            record.apply_url = record.job_url
        valid_records.append(record)

    detected_sources = {record.source for record in valid_records}
    if len(detected_sources) == 1 and next(iter(detected_sources)) in {"greenhouse", "lever", "ashby"}:
        company.platform = next(iter(detected_sources))

    stored: list[Job] = []
    for record in valid_records:
        existing = db.scalar(select(Job).where(Job.job_url == record.job_url))
        if existing:
            existing.company_id = company.id
            existing.title = record.title[:300]
            existing.location = record.location
            existing.employment_type = record.employment_type
            existing.department = record.department
            existing.description = record.description
            existing.apply_url = record.apply_url
            existing.source = record.source
            existing.source_job_id = record.source_job_id
            existing.status = "open"
            stored.append(existing)
            continue

        job = Job(
            company_id=company.id,
            title=record.title[:300],
            location=record.location,
            employment_type=record.employment_type,
            department=record.department,
            description=record.description,
            job_url=record.job_url,
            apply_url=record.apply_url,
            source=record.source,
            source_job_id=record.source_job_id,
            status="open",
        )
        db.add(job)
        stored.append(job)

    db.commit()
    return stored
