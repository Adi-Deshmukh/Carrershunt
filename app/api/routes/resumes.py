import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
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
        content_json=json.dumps(content),
        file_path=str(path),
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    return {
        "resume_id": version.id,
        "filename": path.name,
        "download_url": f"/resumes/{version.id}/download",
        "content": content,
    }


@router.get("/{resume_id}/download")
def download_resume(resume_id: int, db: Session = Depends(get_db)):
    version = db.get(ResumeVersion, resume_id)
    if not version:
        raise HTTPException(status_code=404, detail="Resume not found")
    return FileResponse(
        version.file_path,
        filename=version.filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
