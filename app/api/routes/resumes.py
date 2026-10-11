import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.models import CandidateProfile, Job, PipelineRun, ResumeVersion
from app.db.session import get_db
from app.schemas.agent import ResumePlan
from app.services.resume_quality import validate_resume_quality
from app.services.resume_service import generate_docx_from_plan

router = APIRouter(prefix="/resumes", tags=["resumes"])


def _current_candidate(db: Session, user: dict) -> CandidateProfile | None:
    query = select(CandidateProfile)
    if user.get("id"):
        query = query.where(CandidateProfile.supabase_user_id == user["id"])
    else:
        query = query.where(CandidateProfile.supabase_user_id.is_(None))
    return db.scalar(query.order_by(CandidateProfile.id.desc()))


def _owns_resume(version: ResumeVersion, candidate: CandidateProfile | None, user: dict) -> bool:
    if candidate is None:
        return False
    if user.get("id"):
        return version.candidate_id == candidate.id
    return version.candidate_id in (None, candidate.id)


@router.post("/tailor/{job_id}")
def tailor_resume(job_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Create a DOCX only after the user explicitly requests it for a reviewed job."""
    job = db.get(Job, job_id)
    candidate = _current_candidate(db, user)
    if not job or not candidate:
        raise HTTPException(status_code=404, detail="Job or candidate profile not found")

    run = db.scalar(
        select(PipelineRun)
        .where(
            PipelineRun.job_id == job.id,
            PipelineRun.candidate_id == candidate.id,
            PipelineRun.status.in_(["completed", "completed_with_warnings"]),
        )
        .order_by(PipelineRun.id.desc())
    )
    if not run or not run.result_json:
        raise HTTPException(status_code=409, detail="Analyze this job before creating a tailored resume.")

    result = json.loads(run.result_json)
    raw_plan = result.get("resume")
    if not raw_plan:
        raise HTTPException(status_code=409, detail="No resume plan is available for this job. Re-run job analysis.")

    plan = ResumePlan.model_validate(raw_plan)
    validation_errors = validate_resume_quality(
        plan,
        f"{candidate.resume_text or ''} {candidate.experience_years:g}",
        job.title,
    )
    if validation_errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "Resume plan did not pass quality checks.", "validation_errors": validation_errors},
        )

    path, content = generate_docx_from_plan(candidate, job, plan)
    version = ResumeVersion(
        job_id=job.id,
        candidate_id=candidate.id,
        filename=path.name,
        content_json=json.dumps(content, ensure_ascii=False),
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
def get_resume(resume_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    version = db.get(ResumeVersion, resume_id)
    candidate = _current_candidate(db, user)
    if not version or not _owns_resume(version, candidate, user):
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"resume_id": version.id, "job_id": version.job_id, "filename": version.filename, "content": json.loads(version.content_json), "created_at": version.created_at}


@router.get("/{resume_id}/preview", response_class=HTMLResponse)
def preview_resume(resume_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    version = db.get(ResumeVersion, resume_id)
    candidate = _current_candidate(db, user)
    if not version or not _owns_resume(version, candidate, user):
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
def download_resume(resume_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    version = db.get(ResumeVersion, resume_id)
    candidate = _current_candidate(db, user)
    if not version or not _owns_resume(version, candidate, user) or not version.file_path:
        raise HTTPException(status_code=404, detail="Resume not found")
    return FileResponse(
        version.file_path,
        filename=version.filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
