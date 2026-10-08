import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Job, Person
from app.db.session import get_db
from app.services.ai_service import AIService
from app.services.people_search import SerperPeopleProvider

router = APIRouter(prefix="/people", tags=["people"])


@router.get("/search")
async def search_people(company: str, role: str, skills: str = ""):
    provider = SerperPeopleProvider()
    result = await provider.search(company, role, [s.strip() for s in skills.split(",") if s.strip()])
    return {"results": [r.__dict__ for r in result]}


@router.post("/save/{job_id}")
async def save_people(job_id: int, company: str, role: str, skills: str = "", db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    provider = SerperPeopleProvider()
    result = await provider.search(company, role, [s.strip() for s in skills.split(",") if s.strip()])

    saved = []
    for person in result:
        row = Person(
            company_id=job.company_id,
            name=person.name,
            role=person.role,
            profile_url=person.profile_url,
            public_email=person.public_email,
            relevance_score=person.relevance_score,
            source="public_search",
            rationale=person.rationale,
        )
        db.add(row)
        saved.append(row)

    db.commit()
    return {"saved": len(saved), "people": [p.profile_url for p in saved]}


@router.post("/outreach/{job_id}")
def create_outreach(job_id: int, person_id: int | None = None, db: Session = Depends(get_db)):
    from app.db.models import CandidateProfile, OutreachMessage

    job = db.get(Job, job_id)
    candidate = db.query(CandidateProfile).order_by(CandidateProfile.id.desc()).first()
    person = db.get(Person, person_id) if person_id else None

    if not job or not candidate:
        raise HTTPException(status_code=404, detail="Job or candidate not found")

    ai = AIService()
    if "openai" in ai.configured_providers():
        response = ai.providers["openai"].chat.completions.create(
            model=__import__("app.core.config", fromlist=["settings"]).settings.openai_model,
            messages=[{"role": "user", "content": (
                "Write a concise, professional referral outreach email. "
                "Use only supplied facts. Do not fabricate a relationship. "
                + json.dumps({
                    "candidate": {"name": candidate.name, "resume": candidate.resume_text},
                    "job": {"title": job.title, "company": job.company.name if job.company else ""},
                    "person": {"name": person.name, "role": person.role} if person else None,
                })
            ),
        )
        body = response.output_text
        subject = f"Interested in {job.title}"
    else:
        body = (
            f"Hi {person.name if person else 'there'},\n\n"
            f"I'm {candidate.name} and I'm interested in the {job.title} role. "
            "I'd appreciate any advice you can share about the team or application."
        )
        subject = f"Interested in {job.title}"

    message = OutreachMessage(
        job_id=job_id,
        person_id=person_id,
        channel="email",
        subject=subject,
        body=body,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return {"id": message.id, "subject": subject, "body": body, "status": message.status}
