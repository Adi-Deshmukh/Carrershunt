import json
from pathlib import Path

from docx import Document

from app.db.models import CandidateProfile, Job
from app.services.ai_service import AIService
from app.services.matching import match_job

OUTPUT_DIR = Path("generated_resumes")
OUTPUT_DIR.mkdir(exist_ok=True)


def _candidate_dict(candidate: CandidateProfile) -> dict:
    return {
        "name": candidate.name,
        "education": candidate.education,
        "graduation_year": candidate.graduation_year,
        "experience_years": candidate.experience_years,
        "location": candidate.location,
        "work_authorization": candidate.work_authorization,
        "resume_text": candidate.resume_text,
        "evidence": json.loads(candidate.evidence_json or "{}"),
    }


def _job_dict(job: Job) -> dict:
    return {
        "title": job.title,
        "location": job.location,
        "employment_type": job.employment_type,
        "department": job.department,
        "description": job.description,
        "job_url": job.job_url,
        "company": job.company.name if job.company else "",
    }


def generate_docx(candidate: CandidateProfile, job: Job) -> tuple[Path, dict]:
    match = match_job(job, candidate).model_dump()
    content = AIService().tailor_resume(_candidate_dict(candidate), _job_dict(job), match)

    path = OUTPUT_DIR / f"job_{job.id}_resume.docx"
    doc = Document()
    doc.add_heading(candidate.name, level=0)
    doc.add_paragraph(content.get("summary", ""))

    if content.get("skills"):
        doc.add_heading("Skills", level=1)
        doc.add_paragraph(", ".join(content["skills"]))

    if content.get("projects"):
        doc.add_heading("Relevant Projects", level=1)
        for project in content["projects"]:
            doc.add_heading(project.get("name", "Project"), level=2)
            for bullet in project.get("bullets", []):
                doc.add_paragraph(bullet, style="List Bullet")

    doc.add_heading("Target Role", level=1)
    doc.add_paragraph(job.title)

    doc.save(path)
    return path, content
