import math
import re
from collections import Counter
from typing import Iterable

# Canonical skills keep common spellings and abbreviations comparable across
# job descriptions, resume text, repository metadata, and README files.
SKILL_ALIASES = {
    "scikit-learn": {"sklearn", "scikit learn"},
    "machine learning": {"ml", "machine-learning"},
    "deep learning": {"dl", "deep-learning"},
    "postgresql": {"postgres", "postgre"},
    "javascript": {"js"},
    "typescript": {"ts"},
    "c++": {"cpp"},
    "c#": {"csharp", "c sharp"},
    "github actions": {"github-actions"},
    "ci/cd": {"cicd", "continuous integration", "continuous deployment"},
    "rest api": {"rest", "restful", "rest apis"},
    "node.js": {"nodejs", "node"},
    "next.js": {"nextjs"},
    "pytorch": {"torch"},
    "tensorflow": {"tf"},
    "kubernetes": {"k8s"},
    "vector database": {"vector db", "vectordb"},
}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9+#.-]{2,}", (text or "").lower())


def _expand_tokens(tokens: Iterable[str]) -> set[str]:
    values = set(tokens)
    joined = " ".join(values)
    for canonical, aliases in SKILL_ALIASES.items():
        if canonical in joined or any(alias in joined for alias in aliases):
            values.add(canonical)
            values.update(aliases)
    return values


def _skill_forms(skill: str) -> set[str]:
    canonical = skill.strip().lower()
    aliases = SKILL_ALIASES.get(canonical, set())
    return {canonical, *(alias.lower() for alias in aliases)}


def _contains_skill(searchable: set[str], skill: str) -> bool:
    forms = _skill_forms(skill)
    if forms & searchable:
        return True
    # Multi-token skills should match as phrases, not only as isolated tokens.
    return any(
        len(form.split()) > 1 and form in " ".join(searchable)
        for form in forms
    )


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    common = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def semantic_similarity(job_text: str, candidate_text: str) -> float:
    return round(_cosine(
        Counter(_expand_tokens(_tokens(job_text))),
        Counter(_expand_tokens(_tokens(candidate_text))),
    ), 4)


def hybrid_match_score(
    required_skills: list[str],
    preferred_skills: list[str],
    job_text: str,
    candidate_text: str,
    evidence_skills: set[str] | None = None,
) -> dict:
    evidence_tokens = _expand_tokens(
        token for skill in (evidence_skills or set()) for token in _tokens(skill)
    )
    candidate_tokens = _expand_tokens(_tokens(candidate_text))
    searchable = candidate_tokens | evidence_tokens
    candidate_corpus = (candidate_text or "").lower()

    def covered(skill: str) -> bool:
        forms = _skill_forms(skill)
        if forms & searchable:
            return True
        return any(
            re.search(rf"(?<![a-z0-9]){re.escape(form)}(?![a-z0-9])", candidate_corpus)
            for form in forms
        )

    def coverage(skills: list[str]) -> float:
        return (sum(covered(skill) for skill in skills) / len(skills)) if skills else 1.0

    required_coverage = coverage(required_skills)
    preferred_coverage = coverage(preferred_skills)
    similarity = semantic_similarity(job_text, candidate_text)
    score = (
        0.65 * required_coverage
        + 0.15 * preferred_coverage
        + 0.20 * similarity
    ) * 100
    matched_required = [skill for skill in required_skills if covered(skill)]
    return {
        "score": round(min(100.0, score), 1),
        "semantic_similarity": similarity,
        "required_skill_coverage": round(required_coverage, 4),
        "preferred_skill_coverage": round(preferred_coverage, 4),
        "matched_required_skills": matched_required,
        "gaps": [skill for skill in required_skills if skill not in matched_required],
    }
