from pathlib import Path

from docx import Document

from app.db.models import CandidateProfile, Job

OUTPUT_DIR = Path("generated_resumes")
OUTPUT_DIR.mkdir(exist_ok=True)


def generate_docx(candidate: CandidateProfile, job: Job, tailored: dict) -> tuple[Path, dict]:
    path = OUTPUT_DIR / f"job_{job.id}_resume.docx"

    doc = Document()
    doc.add_heading(candidate.name, level=0)
    doc.add_paragraph(tailored.get("summary", ""))

    if tailored.get("skills"):
        doc.add_heading("Relevant Skills", level=1)
        for skill in tailored["skills"]:
            doc.add_paragraph(skill, style="List Bullet")

    if tailored.get("projects"):
        doc.add_heading("Projects & Experience", level=1)
        for project in tailored["projects"]:
            doc.add_heading(project.get("name", "Project"), level=2)
            for bullet in project.get("bullets", []):
                doc.add_paragraph(bullet, style="List Bullet")

    doc.add_heading("Education & Background", level=1)
    doc.add_paragraph(candidate.education or "")
    doc.add_paragraph(candidate.resume_text)

    doc.save(path)
    return path, tailored
