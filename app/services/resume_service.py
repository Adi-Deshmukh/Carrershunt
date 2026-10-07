import json
from pathlib import Path

from docx import Document

from app.db.models import CandidateProfile, Job
from app.services.matching import match_job

OUTPUT_DIR = Path("generated_resumes")
OUTPUT_DIR.mkdir(exist_ok=True)


def build_resume_content(candidate: CandidateProfile, job: Job) -> dict:
    match = match_job(job, candidate)
    sections = [line.strip() for line in candidate.resume_text.splitlines() if line.strip()]

    return {
        "name": candidate.name,
        "target_role": job.title,
        "summary": (
            f"{candidate.name} — candidate profile tailored for {job.title} at the target company. "
            f"Emphasized evidence: {', '.join(match.evidence)}"
        ),
        "resume_lines": sections,
        "matched_skills": match.evidence,
        "gaps": match.gaps,
    }


def generate_docx(candidate: CandidateProfile, job: Job) -> tuple[Path, dict]:
    content = build_resume_content(candidate, job)
    path = OUTPUT_DIR / f"job_{job.id}_resume.docx"

    doc = Document()
    doc.add_heading(candidate.name, level=0)
    doc.add_paragraph(content["summary"])
    doc.add_heading("Target Role", level=1)
    doc.add_paragraph(job.title)

    doc.add_heading("Master Resume Content", level=1)
    for line in content["resume_lines"]:
        doc.add_paragraph(line)

    doc.add_heading("Relevant Evidence", level=1)
    for item in content["matched_skills"]:
        doc.add_paragraph(item, style="List Bullet")

    doc.save(path)
    return path, content
