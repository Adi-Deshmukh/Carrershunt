import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import CandidateEvidence, CandidateProfile
from app.db.session import get_db
from app.schemas.evidence import EvidenceSearchRequest
from app.services.evidence import retrieve_evidence

router = APIRouter(prefix="/candidates", tags=["candidate-evidence"])


@router.get("/{candidate_id}/evidence")
def list_evidence(candidate_id: int, db: Session = Depends(get_db)):
    records = db.query(CandidateEvidence).filter(
        CandidateEvidence.candidate_id == candidate_id
    ).order_by(CandidateEvidence.id.desc()).all()

    return [{
        "id": r.id,
        "source": r.source,
        "source_key": r.source_key,
        "type": r.evidence_type,
        "title": r.title,
        "content": r.content,
        "url": r.url,
        "skills": json.loads(r.metadata_json or "{}").get("skills", []),
        "metadata": json.loads(r.metadata_json or "{}").get("metadata", {}),
    } for r in records]


@router.post("/{candidate_id}/evidence/search")
def search_evidence(
    candidate_id: int,
    data: EvidenceSearchRequest,
    db: Session = Depends(get_db),
):
    if not db.get(CandidateProfile, candidate_id):
        raise HTTPException(status_code=404, detail="Candidate not found")
    results = retrieve_evidence(
        db,
        candidate_id,
        data.query,
        limit=data.limit,
        evidence_type=data.evidence_type,
    )
    return {"query": data.query, "results": results}
