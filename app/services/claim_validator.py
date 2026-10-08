import re


def normalize_claim(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def validate_claims(claims: list[str], evidence: list[dict], candidate_text: str) -> list[str]:
    corpus = " ".join(
        [candidate_text]
        + [str(item.get("content", "")) for item in evidence]
        + [str(item.get("title", "")) for item in evidence]
    )
    normalized_corpus = normalize_claim(corpus)
    errors = []
    for claim in claims:
        normalized = normalize_claim(claim)
        if not normalized:
            errors.append("Empty factual claim.")
            continue
        # Conservative validation: every meaningful phrase must be grounded.
        words = [w for w in re.findall(r"[a-z0-9+#.-]{3,}", normalized) if w not in {"the","and","with","for","from"}]
        if words and sum(word in normalized_corpus for word in words) / len(words) < 0.55:
            errors.append(f"Unsupported claim: {claim}")
    return errors


def validate_resume_plan(plan, evidence: list[dict], candidate_text: str) -> list[str]:
    errors = validate_claims(plan.claims, evidence, candidate_text)
    for project in plan.projects:
        for bullet in project.bullets:
            errors.extend(validate_claims([bullet], evidence, candidate_text))
    return errors
