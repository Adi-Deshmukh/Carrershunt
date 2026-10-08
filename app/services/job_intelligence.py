import re

from app.db.models import Job
from app.schemas.agent import StructuredJob
from app.services.ai_service import AIService


SKILLS = [
    "python", "java", "c++", "javascript", "typescript", "react", "django", "fastapi",
    "postgresql", "sql", "docker", "kubernetes", "aws", "azure", "gcp", "tensorflow",
    "pytorch", "scikit-learn", "machine learning", "deep learning", "git", "github",
    "linux", "data science", "nlp", "llm", "rest", "ci/cd", "github actions",
]


def _contains(text: str, term: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.I) is not None


def parse_job(job: Job) -> StructuredJob:
    text = f"{job.title}\n{job.description or ''}"
    required = [skill for skill in SKILLS if _contains(text, skill)]
    years = 0.0
    patterns = [
        r"(\d+(?:\.\d+)?)\s*\+?\s*years?\s+(?:of\s+)?experience",
        r"(?:minimum|at least)\s+(\d+(?:\.\d+)?)\s*years?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            years = max(years, float(match.group(1)))

    education = []
    for term in ("bachelor", "b.tech", "b.s.", "master", "m.tech", "m.s."):
        if _contains(text, term):
            education.append(term)

    authorization = []
    if re.search(r"work authorization|authorized to work|visa sponsorship", text, re.I):
        authorization.append("authorized")

    seniority = None
    for level in ("intern", "entry", "junior", "mid", "senior", "staff", "principal"):
        if re.search(rf"\b{level}\b", job.title, re.I):
            seniority = level
            break

    responsibilities = [
        line.strip(" -•")
        for line in re.split(r"[\n\r]+", job.description or "")
        if len(line.strip()) >= 25
    ][:12]

    return StructuredJob(
        title=job.title,
        company=job.company.name if job.company else "",
        location=job.location,
        employment_type=job.employment_type,
        seniority=seniority,
        required_skills=required,
        preferred_skills=[],
        required_years_experience=years,
        education_requirements=education,
        authorization_requirements=authorization,
        responsibilities=responsibilities,
        qualifications=[],
    )


def enrich_job_with_llm(job: Job, structured: StructuredJob) -> StructuredJob:
    ai = AIService()
    return ai.structure_job(
        {
            "title": job.title,
            "company": job.company.name if job.company else "",
            "location": job.location,
            "employment_type": job.employment_type,
            "description": job.description,
        },
        structured.model_dump(),
    )
