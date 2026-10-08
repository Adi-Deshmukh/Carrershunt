import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
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


@router.get("/{resume_id}")
def get_resume(resume_id: int, db: Session = Depends(get_db)):
    version = db.get(ResumeVersion, resume_id)
    if not version:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"resume_id": version.id, "job_id": version.job_id, "filename": version.filename, "content": json.loads(version.content_json), "created_at": version.created_at}


@router.get("/{resume_id}/preview", response_class=HTMLResponse)
def preview_resume(resume_id: int, db: Session = Depends(get_db)):
    version = db.get(ResumeVersion, resume_id)
    if not version:
        raise HTTPException(status_code=404, detail="Resume not found")
    content = json.loads(version.content_json)
    import html
    esc = html.escape
    skills = ", ".join(esc(str(x)) for x in content.get("skills", []))
    projects = "".join(
        f"<h3>{esc(str(p.get('name', 'Project')))}</h3><ul>"
        + "".join(f"<li>{esc(str(b))}</li>" for b in p.get("bullets", []))
        + "</ul>" for p in content.get("projects", [])
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><title>Resume Preview</title>"
        "<style>body{font:14px Arial;color:#222;max-width:850px;margin:40px auto;line-height:1.5}"
        "h1{margin-bottom:4px}h2{border-bottom:1px solid #ddd;padding-bottom:4px}</style></head><body>"
        f"<h1>Resume Preview</h1><h2>Summary</h2><p>{esc(str(content.get('summary','')))}</p>"
        f"<h2>Skills</h2><p>{skills}</p><h2>Projects</h2>{projects}</body></html>"
    )
    return HTMLResponse(page)


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
