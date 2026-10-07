from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Company, Job, Person
from app.db.session import get_db
from app.services.people_search import SerperPeopleProvider

router = APIRouter(prefix="/people", tags=["people"])


@router.get("/search")
async def search_people(company: str, role: str, skills: str = ""):
    provider = SerperPeopleProvider()
    results = await provider.search(company, role, [s.strip() for s in skills.split(",") if s.strip()])
    return {"results": [r.__dict__ for r in results]}


@router.post("/save/{job_id}")
async def save_people(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    company = db.get(Company, job.company_id)
    provider = SerperPeopleProvider()
    results = await provider.search(company.name, job.title, [])

    saved = []
    for item in results:
        existing = db.scalar(select(Person).where(Person.profile_url == item.profile_url))
        if existing:
            saved.append(existing)
            continue
        person = Person(
            company_id=company.id,
            name=item.name,
            role=item.role,
            profile_url=item.profile_url,
            public_email=item.public_email,
            relevance_score=item.relevance_score,
            source="serper",
            rationale=item.rationale,
        )
        db.add(person)
        saved.append(person)

    db.commit()
    return {"job_id": job.id, "people": [
        {"id": p.id, "name": p.name, "role": p.role, "profile_url": p.profile_url, "relevance_score": p.relevance_score}
        for p in saved
    ]}
