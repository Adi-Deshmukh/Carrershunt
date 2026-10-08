import re

from app.schemas.agent import ResumePlan

PLACEHOLDERS = {"lorem ipsum", "your name", "company name", "insert", "todo", "tbd"}


def validate_resume_quality(plan: ResumePlan, candidate_text: str, job_title: str) -> list[str]:
    errors: list[str] = []
    source = (candidate_text or "").lower()
    output = " ".join([plan.summary, *plan.skills] + [p.name for p in plan.projects] + [b for p in plan.projects for b in p.bullets] + plan.claims).lower()
    if len(plan.summary.strip()) < 30:
        errors.append("Resume summary is too short.")
    if not plan.skills and not plan.projects:
        errors.append("Tailored resume contains neither skills nor relevant projects.")
    for placeholder in PLACEHOLDERS:
        if placeholder in output:
            errors.append(f"Resume contains placeholder text: {placeholder}.")
    source_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", source))
    for number in re.findall(r"\b\d+(?:\.\d+)?\b", output):
        if number not in source_numbers:
            errors.append(f"Resume contains unsupported numeric claim: {number}.")
            break
    title_tokens = [t for t in re.findall(r"[a-z0-9+#.-]{3,}", job_title.lower())]
    if title_tokens and not any(token in output for token in title_tokens):
        errors.append("Tailored resume does not reference the target role.")
    return errors
