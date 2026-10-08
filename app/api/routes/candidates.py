import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CandidateProfile, CandidateEvidence
from app.db.session import get_db
from app.schemas.candidate import CandidateCreate, CandidateUpdate
from app.services.evidence import EvidenceInput, upsert_evidence

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("")
def create_candidate(data: CandidateCreate, db: Session = Depends(get_db)):
    candidate = CandidateProfile(
        name=data.name,
        email=data.email,
        education=data.education,
        graduation_year=data.graduation_year,
        experience_years=data.experience_years,
        location=data.location,
        work_authorization=data.work_authorization,
        resume_text=data.resume_text,
        evidence_json=json.dumps(data.evidence, ensure_ascii=False),
    )
    db.add(candidate)
    db.flush()

    upsert_evidence(
        db,
        candidate.id,
        EvidenceInput(
            source="resume",
            source_key="profile",
            title="Candidate profile resume",
            content=data.resume_text,
            evidence_type="resume",
        ),
    )

    for key, value in data.evidence.items():
        if value is None:
            continue
        content = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        upsert_evidence(
            db,
            candidate.id,
            EvidenceInput(
                source="candidate",
                source_key=f"profile:{key}",
                title=str(key),
                content=content,
                evidence_type="candidate",
            ),
        )

    db.commit()
    db.refresh(candidate)
    return {"id": candidate.id, "name": candidate.name, "evidence_indexed": len(data.evidence) + 1}


@router.get("/latest")
def get_latest_candidate(db: Session = Depends(get_db)):
    candidate = db.scalar(select(CandidateProfile).order_by(CandidateProfile.id.desc()))
    if not candidate:
        return None
    evidence_count = db.scalar(
        select(CandidateEvidence.id)
        .where(CandidateEvidence.candidate_id == candidate.id)
        .order_by(CandidateEvidence.id.desc())
        .limit(1)
    )
    return {
        "id": candidate.id,
        "name": candidate.name,
        "email": candidate.email,
        "education": candidate.education,
        "graduation_year": candidate.graduation_year,
        "experience_years": candidate.experience_years,
        "location": candidate.location,
        "work_authorization": candidate.work_authorization,
        "resume_text": candidate.resume_text,
        "evidence": json.loads(candidate.evidence_json or "{}"),
        "has_evidence": evidence_count is not None,
    }
