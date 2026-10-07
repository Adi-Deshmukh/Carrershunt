import json
import re

from app.db.models import CandidateProfile, Job
from app.schemas.matching import MatchResult

SKILL_PATTERNS = re.compile(
    r"\b(python|java|c\+\+|javascript|typescript|react|django|fastapi|"
    r"postgresql|sql|docker|kubernetes|aws|azure|gcp|tensorflow|pytorch|"
    r"scikit-learn|machine learning|deep learning|git|github|linux|"
    r"data science|nlp|llm|api|rest|ci/cd|github actions)\b",
    re.I,
)


def _skills(text: str) -> set[str]:
    return {m.group(1).lower() for m in SKILL_PATTERNS.finditer(text or "")}


def match_job(job: Job, candidate: CandidateProfile) -> MatchResult:
    jd = job.description or ""
    candidate_text = " ".join(
        [
            candidate.resume_text or "",
            candidate.education or "",
            candidate.evidence_json or "",
        ]
    )

    required = _skills(jd)
    known = _skills(candidate_text)
    matched = sorted(required & known)
    missing = sorted(required - known)

    technical = 100.0 if not required else (len(matched) / len(required)) * 100

    hard_experience = re.search(r"(\d+)\+?\s+years?\s+(?:of\s+)?experience", jd, re.I)
    required_years = float(hard_experience.group(1)) if hard_experience else 0.0
    eligible = candidate.experience_years >= required_years

    education_required = bool(re.search(r"bachelor|b\.s\.|b\.tech|undergraduate", jd, re.I))
    education_ok = bool(candidate.education) if education_required else True

    eligible = eligible and education_ok

    fit = round(
        0.60 * technical
        + 0.20 * min(100.0, candidate.experience_years / max(required_years, 1) * 100)
        + 0.20 * (100 if education_ok else 0),
        1,
    )
    if not eligible:
        fit = min(fit, 49.0)

    if fit >= 85 and eligible:
        estimate = "high"
    elif fit >= 70 and eligible:
        estimate = "moderate-high"
    elif fit >= 55 and eligible:
        estimate = "moderate"
    else:
        estimate = "low"

    evidence = [
        f"Matched skills: {', '.join(matched)}" if matched else "No explicit technical skill overlap found."
    ]

    explanation = (
        f"Technical alignment is {technical:.0f}%. "
        f"{len(matched)} of {len(required)} detected JD skills overlap with the candidate evidence. "
        f"Eligibility checks: experience={'pass' if candidate.experience_years >= required_years else 'fail'}, "
        f"education={'pass' if education_ok else 'fail'}."
    )

    return MatchResult(
        job_id=job.id,
        eligible=eligible,
        fit_score=fit,
        interview_estimate=estimate,
        confidence="medium",
        explanation=explanation,
        gaps=missing,
        evidence=evidence,
    )


def serialize_match(result: MatchResult) -> tuple[str, str]:
    return json.dumps(result.gaps), json.dumps(result.evidence)
