from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.models import CandidateProfile
from app.db.session import get_db
from app.services.evidence import EvidenceInput, upsert_evidence
from app.services.resume_parser import extract_resume_text

router = APIRouter(prefix="/candidates", tags=["candidate-resume"])


@router.post("/{candidate_id}/resume")
async def upload_master_resume(
    candidate_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    candidate = db.get(CandidateProfile, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    content = await file.read()
    try:
        text = extract_resume_text(file.filename or "", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    candidate.resume_text = text
    upsert_evidence(
        db,
        candidate_id,
        EvidenceInput(
            source="resume",
            source_key="master",
            title="Master resume",
            content=text,
            evidence_type="resume",
            url=None,
            metadata={"filename": file.filename},
        ),
    )
    db.commit()

    return {
        "candidate_id": candidate_id,
        "filename": file.filename,
        "characters_extracted": len(text),
        "status": "indexed",
    }
