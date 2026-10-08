import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CandidateEvidence

STOPWORDS = {
    "and","the","for","with","from","that","this","into","using","have","has",
    "your","you","are","our","job","role","work","experience","years","team",
    "build","built","use","used","developer","engineer","software","data"
}


def _tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9+#.-]{2,}", (text or "").lower())
        if token not in STOPWORDS
    }


def fingerprint(
    candidate_id: int,
    source: str,
    source_key: str,
    content: str,
) -> str:
    """Create a candidate-scoped fingerprint for idempotent evidence upserts."""
    raw = f"{candidate_id}|{source}|{source_key}|{content}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class EvidenceInput:
    source: str
    source_key: str
    title: str
    content: str
    url: str | None = None
    evidence_type: str = "project"
    skills: list[str] | None = None
    metadata: dict[str, Any] | None = None


def upsert_evidence(db: Session, candidate_id: int, item: EvidenceInput) -> CandidateEvidence:
    content = item.content.strip()
    if not content:
        raise ValueError("Evidence content cannot be empty")

    fp = fingerprint(candidate_id, item.source, item.source_key, content)
    existing = db.scalar(
        select(CandidateEvidence).where(
            CandidateEvidence.candidate_id == candidate_id,
            CandidateEvidence.fingerprint == fp,
        )
    )
    payload = {
        "skills": sorted(set(item.skills or [])),
        "metadata": item.metadata or {},
    }

    if existing:
        existing.title = item.title[:300]
        existing.content = content
        existing.url = item.url
        existing.evidence_type = item.evidence_type
        existing.metadata_json = json.dumps(payload, ensure_ascii=False)
        return existing

    record = CandidateEvidence(
        candidate_id=candidate_id,
        source=item.source,
        source_key=item.source_key,
        title=item.title[:300],
        content=content,
        url=item.url,
        evidence_type=item.evidence_type,
        metadata_json=json.dumps(payload, ensure_ascii=False),
        fingerprint=fp,
    )
    db.add(record)
    return record


def retrieve_evidence(
    db: Session,
    candidate_id: int,
    query: str,
    limit: int = 8,
    evidence_type: str | None = None,
) -> list[dict[str, Any]]:
    if limit < 1 or limit > 50:
        raise ValueError("limit must be between 1 and 50")

    stmt = select(CandidateEvidence).where(CandidateEvidence.candidate_id == candidate_id)
    if evidence_type:
        stmt = stmt.where(CandidateEvidence.evidence_type == evidence_type)

    records = db.scalars(stmt).all()
    query_tokens = _tokens(query)
    ranked: list[tuple[float, CandidateEvidence]] = []

    for record in records:
        payload = json.loads(record.metadata_json or "{}")
        skills = payload.get("skills", [])
        haystack = _tokens(
            " ".join([record.title, record.content, " ".join(skills)])
        )
        overlap = query_tokens & haystack
        if not query_tokens:
            score = 0.0
        else:
            score = len(overlap) / len(query_tokens)
            if skills and query_tokens.intersection(_tokens(" ".join(skills))):
                score += 0.25
            if record.source == "github":
                score += 0.02
        ranked.append((score, record))

    ranked.sort(key=lambda pair: (pair[0], pair[1].id or 0), reverse=True)
    results = []
    for score, record in ranked[:limit]:
        payload = json.loads(record.metadata_json or "{}")
        results.append({
            "id": record.id,
            "source": record.source,
            "source_key": record.source_key,
            "type": record.evidence_type,
            "title": record.title,
            "content": record.content,
            "url": record.url,
            "skills": payload.get("skills", []),
            "metadata": payload.get("metadata", {}),
            "score": round(score, 4),
        })
    return results
