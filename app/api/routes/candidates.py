import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.models import CandidateProfile, CandidateEvidence
from app.db.session import get_db
from app.schemas.candidate import CandidateCreate, CandidateUpdate
from app.services.evidence import EvidenceInput, upsert_evidence

router = APIRouter(prefix="/candidates", tags=["candidates"])


def _candidate_for_user(db: Session, user: dict) -> CandidateProfile | None:
    statement = select(CandidateProfile).order_by(CandidateProfile.id.desc())
    if user.get("id"):
        statement = statement.where(CandidateProfile.supabase_user_id == user["id"])
    else:
        statement = statement.where(CandidateProfile.supabase_user_id.is_(None))
    return db.scalar(statement)


def _owns_candidate(candidate: CandidateProfile, user: dict) -> bool:
    return candidate.supabase_user_id == user.get("id")


def _save_evidence(db: Session, candidate: CandidateProfile, evidence: dict) -> None:
    upsert_evidence(
        db,
        candidate.id,
        EvidenceInput(
            source="resume",
            source_key="profile",
            title="Candidate profile resume",
            content=candidate.resume_text,
            evidence_type="resume",
        ),
    )
    for key, value in evidence.items():
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


@router.post("")
def create_candidate(
    data: CandidateCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    candidate = _candidate_for_user(db, user)
    if candidate is None:
        candidate = CandidateProfile(
            supabase_user_id=user.get("id"),
            name=data.name,
            email=data.email or user.get("email"),
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
    else:
        for field in (
            "name", "education", "graduation_year", "experience_years",
            "location", "work_authorization", "resume_text",
        ):
            setattr(candidate, field, getattr(data, field))
        candidate.email = data.email or user.get("email") or candidate.email
        candidate.evidence_json = json.dumps(data.evidence, ensure_ascii=False)

    _save_evidence(db, candidate, data.evidence)
    db.commit()
    db.refresh(candidate)
    return {"id": candidate.id, "name": candidate.name, "evidence_indexed": len(data.evidence) + 1}


@router.patch("/{candidate_id}")
def update_candidate(
    candidate_id: int,
    data: CandidateUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    candidate = db.get(CandidateProfile, candidate_id)
    if not candidate or not _owns_candidate(candidate, user):
        raise HTTPException(status_code=404, detail="Candidate not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(candidate, field, value)
    db.commit()
    db.refresh(candidate)
    return {"id": candidate.id, "name": candidate.name}


@router.get("/latest")
def get_latest_candidate(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    candidate = _candidate_for_user(db, user)
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
