from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CandidateProfile, Job, ResumeVersion
from app.db.session import get_db
from app.services.resume_service import generate_docx

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/tailor/{job_id}")
def tailor_resume(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    candidate = db.scalar(select(CandidateProfile).order_by(CandidateProfile.id.desc()))
    if not job or not candidate:
        raise HTTPException(status_code=404, detail="Job or candidate profile not found")

    path, content = generate_docx(candidate, job)
    version = ResumeVersion(
        job_id=job.id,
        filename=path.name,
        content_json=__import__("json").dumps(content),
        file_path=str(path),
    )
    db.add(version)
    db.commit()
    return {"resume_id": version.id, "filename": path.name, "path": str(path)}
