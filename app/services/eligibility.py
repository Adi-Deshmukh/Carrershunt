import re

from app.db.models import CandidateProfile, Job
from app.schemas.agent import StructuredJob


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower()


def evaluate_hard_eligibility(
    candidate: CandidateProfile,
    job: Job,
    structured: StructuredJob,
) -> tuple[bool, list[str]]:
    failures: list[str] = []

    if structured.required_years_experience > candidate.experience_years:
        failures.append(
            f"Requires {structured.required_years_experience:g}+ years of experience; "
            f"candidate has {candidate.experience_years:g}."
        )

    if structured.education_requirements:
        education = _normalize(candidate.education)
        if not education:
            failures.append("Required education is not present in the candidate profile.")
        elif not any(req.lower() in education for req in structured.education_requirements):
            # Only treat explicit degree requirements as hard failures.
            if any(re.search(r"bachelor|b\.tech|b\.s\.|master|m\.tech|m\.s\.", req, re.I)
                   for req in structured.education_requirements):
                failures.append("Candidate education does not satisfy the stated degree requirement.")

    if structured.authorization_requirements:
        auth = _normalize(candidate.work_authorization)
        if auth and not any(token in auth for token in structured.authorization_requirements):
            failures.append("Candidate work authorization does not match the stated requirement.")
        elif not auth:
            failures.append("Work authorization is required but not provided.")

    if structured.location and candidate.location:
        job_location = _normalize(structured.location)
        candidate_location = _normalize(candidate.location)
        if "remote" not in job_location and candidate_location not in job_location and job_location not in candidate_location:
            # Location is informational unless the JD clearly says relocation/on-site is mandatory.
            location_text = _normalize(job.description)
            if any(term in location_text for term in ("must be located", "must reside", "on-site only", "onsite only")):
                failures.append(f"Required location '{structured.location}' does not match candidate location.")

    return not failures, failures
