import math
import re
from collections import Counter
from typing import Iterable

SKILL_ALIASES = {
    "scikit-learn": {"sklearn", "scikit learn"},
    "machine learning": {"ml", "machine-learning"},
    "deep learning": {"dl", "deep-learning"},
    "postgresql": {"postgres"},
    "javascript": {"js"},
    "typescript": {"ts"},
    "c++": {"cpp"},
    "github actions": {"github-actions"},
    "ci/cd": {"cicd", "continuous integration", "continuous deployment"},
    "rest": {"rest api", "restful"},
}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9+#.-]{2,}", (text or "").lower())


def _expand_tokens(tokens: Iterable[str]) -> set[str]:
    values = set(tokens)
    for canonical, aliases in SKILL_ALIASES.items():
        if canonical in values or values.intersection(aliases):
            values.add(canonical)
            values.update(aliases)
    return values


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
    return round(_cosine(Counter(_expand_tokens(_tokens(job_text))), Counter(_expand_tokens(_tokens(candidate_text)))), 4)


def hybrid_match_score(required_skills: list[str], preferred_skills: list[str], job_text: str, candidate_text: str, evidence_skills: set[str] | None = None) -> dict:
    evidence_skills = {skill.lower() for skill in (evidence_skills or set())}
    candidate_tokens = _expand_tokens(_tokens(candidate_text))
    searchable = candidate_tokens | evidence_skills

    def coverage(skills: list[str]) -> float:
        if not skills:
            return 1.0
        matched = 0
        for skill in skills:
            aliases = {skill.lower()} | {a.lower() for a in SKILL_ALIASES.get(skill.lower(), set())}
            if aliases & searchable:
                matched += 1
        return matched / len(skills)

    required_coverage = coverage(required_skills)
    preferred_coverage = coverage(preferred_skills)
    similarity = semantic_similarity(job_text, candidate_text)
    score = (0.55 * required_coverage + 0.15 * preferred_coverage + 0.30 * similarity) * 100
    matched_required = [skill for skill in required_skills if ({skill.lower()} | {a.lower() for a in SKILL_ALIASES.get(skill.lower(), set())}) & searchable]
    return {
        "score": round(min(100.0, score), 1),
        "semantic_similarity": similarity,
        "required_skill_coverage": round(required_coverage, 4),
        "preferred_skill_coverage": round(preferred_coverage, 4),
        "matched_required_skills": matched_required,
        "gaps": [skill for skill in required_skills if skill not in matched_required],
    }
