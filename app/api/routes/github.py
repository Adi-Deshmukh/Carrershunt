from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import CandidateProfile
from app.db.session import get_db
from app.schemas.evidence import GitHubSyncRequest
from app.services.github_service import sync_github

router = APIRouter(prefix="/candidates", tags=["github"])


@router.post("/{candidate_id}/github/sync")
async def github_sync(
    candidate_id: int,
    data: GitHubSyncRequest,
    db: Session = Depends(get_db),
):
    if not db.get(CandidateProfile, candidate_id):
        raise HTTPException(status_code=404, detail="Candidate not found")

    try:
        result = await sync_github(
            db,
            candidate_id,
            data.username_or_url,
            max_repos=data.max_repos,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "candidate_id": candidate_id,
        "username": result.username,
        "repositories_seen": result.repositories_seen,
        "repositories_indexed": result.repositories_indexed,
        "evidence_created_or_updated": result.evidence_created_or_updated,
        "rate_limit_remaining": result.rate_limit_remaining,
    }
