import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CandidateProfile, Job, ResumeVersion
from app.db.session import get_db
from app.services.ai_service import AIService
from app.services.matching import match_job
from app.services.resume_service import generate_docx

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/tailor/{job_id}")
def tailor_resume(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    candidate = db.scalar(select(CandidateProfile).order_by(CandidateProfile.id.desc()))
    if not job or not candidate:
        raise HTTPException(status_code=404, detail="Job or candidate profile not found")

    match = match_job(job, candidate).model_dump()
    ai = AIService()
    tailored = ai.tailor_resume(
        {
            "name": candidate.name,
            "education": candidate.education,
            "experience_years": candidate.experience_years,
            "resume_text": candidate.resume_text,
            "evidence": json.loads(candidate.evidence_json or "{}"),
        },
        {
            "title": job.title,
            "description": job.description,
            "location": job.location,
            "department": job.department,
            "job_url": job.job_url,
        },
        match,
    )

    path, _ = generate_docx(candidate, job, tailored)
    version = ResumeVersion(
        job_id=job.id,
        filename=path.name,
        content_json=json.dumps(tailored),
        file_path=str(path),
    )
    db.add(version)
    db.commit()
    return {
        "resume_id": version.id,
        "filename": path.name,
        "path": str(path),
        "tailored": tailored,
        "match": match,
    }
