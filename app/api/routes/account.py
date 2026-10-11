from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.models import (
    Application,
    CandidateEvidence,
    CandidateProfile,
    Company,
    IngestionRun,
    IngestionTask,
    Job,
    JobMatch,
    OutreachMessage,
    Person,
    PipelineRun,
    ResumeVersion,
    UserApplication,
)
from app.db.session import get_db

router = APIRouter(prefix="/account", tags=["account"])


@router.post("/reset")
def reset_account_workspace(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Remove this signed-in user's workspace so they can re-import from a clean slate.

    Auth identity and the Supabase public profile row are intentionally retained.
    Company/job rows are removed only when no other ingestion run or candidate
    artifact references them, because older database versions stored those rows
    globally rather than with an explicit owner.
    """
    owner_id = user.get("id")
    if not owner_id:
        raise HTTPException(status_code=401, detail="A signed-in account is required to reset workspace data.")

    runs = db.scalars(
        select(IngestionRun).where(IngestionRun.supabase_user_id == owner_id)
    ).all()
    run_ids = [run.id for run in runs]
    tasks = db.scalars(
        select(IngestionTask).where(IngestionTask.run_id.in_(run_ids))
    ).all() if run_ids else []
    if any(task.status == "running" for task in tasks):
        raise HTTPException(
            status_code=409,
            detail="A company crawl is still running. Wait for it to finish, then reset your workspace.",
        )

    company_ids = sorted({task.company_id for task in tasks if task.company_id is not None})
    candidates = db.scalars(
        select(CandidateProfile).where(CandidateProfile.supabase_user_id == owner_id)
    ).all()
    candidate_ids = [candidate.id for candidate in candidates]

    safe_company_ids: list[int] = []
    for company_id in company_ids:
        other_task = db.scalar(
            select(IngestionTask.id)
            .join(IngestionRun, IngestionTask.run_id == IngestionRun.id)
            .where(
                IngestionTask.company_id == company_id,
                IngestionRun.supabase_user_id.is_not(None),
                IngestionRun.supabase_user_id != owner_id,
            )
            .limit(1)
        )
        if other_task is not None:
            continue

        job_ids = list(db.scalars(select(Job.id).where(Job.company_id == company_id)))
        if not job_ids:
            safe_company_ids.append(company_id)
            continue

        other_pipeline = db.scalar(
            select(PipelineRun.id)
            .join(Job, PipelineRun.job_id == Job.id)
            .where(Job.id.in_(job_ids), PipelineRun.candidate_id.not_in(candidate_ids))
            .limit(1)
        )
        other_resume = db.scalar(
            select(ResumeVersion.id)
            .where(
                ResumeVersion.job_id.in_(job_ids),
                or_(ResumeVersion.candidate_id.is_(None), ResumeVersion.candidate_id.not_in(candidate_ids)),
            )
            .limit(1)
        )
        other_application = db.scalar(
            select(UserApplication.id)
            .where(UserApplication.job_id.in_(job_ids), UserApplication.supabase_user_id != owner_id)
            .limit(1)
        )
        if not any((other_pipeline, other_resume, other_application)):
            safe_company_ids.append(company_id)

    # Delete the current account's candidate artifacts first.
    if candidate_ids:
        db.execute(delete(PipelineRun).where(PipelineRun.candidate_id.in_(candidate_ids)))
        db.execute(delete(ResumeVersion).where(ResumeVersion.candidate_id.in_(candidate_ids)))
        db.execute(delete(CandidateEvidence).where(CandidateEvidence.candidate_id.in_(candidate_ids)))
    db.execute(delete(UserApplication).where(UserApplication.supabase_user_id == owner_id))
    db.execute(delete(IngestionTask).where(IngestionTask.run_id.in_(run_ids))) if run_ids else None
    db.execute(delete(IngestionRun).where(IngestionRun.id.in_(run_ids))) if run_ids else None
    db.execute(delete(CandidateProfile).where(CandidateProfile.id.in_(candidate_ids))) if candidate_ids else None

    deleted_jobs = 0
    if safe_company_ids:
        safe_job_ids = list(db.scalars(select(Job.id).where(Job.company_id.in_(safe_company_ids))))
        if safe_job_ids:
            db.execute(delete(JobMatch).where(JobMatch.job_id.in_(safe_job_ids)))
            db.execute(delete(OutreachMessage).where(OutreachMessage.job_id.in_(safe_job_ids)))
            db.execute(delete(Application).where(Application.job_id.in_(safe_job_ids)))
            db.execute(delete(UserApplication).where(UserApplication.job_id.in_(safe_job_ids)))
            # Remove any remaining legacy artifacts for jobs that were proven unshared.
            db.execute(delete(PipelineRun).where(PipelineRun.job_id.in_(safe_job_ids)))
            db.execute(delete(ResumeVersion).where(ResumeVersion.job_id.in_(safe_job_ids)))
            db.execute(delete(IngestionTask).where(IngestionTask.job_id.in_(safe_job_ids)))
            deleted_jobs = len(safe_job_ids)
            db.execute(delete(Job).where(Job.id.in_(safe_job_ids)))
        # Remove any legacy anonymous task references before deleting companies.
        db.execute(delete(IngestionTask).where(IngestionTask.company_id.in_(safe_company_ids)))
        db.execute(delete(Person).where(Person.company_id.in_(safe_company_ids)))
        db.execute(delete(Company).where(Company.id.in_(safe_company_ids)))

    db.commit()
    return {
        "status": "reset",
        "candidate_profiles_removed": len(candidate_ids),
        "ingestion_runs_removed": len(run_ids),
        "companies_removed": len(safe_company_ids),
        "jobs_removed": deleted_jobs,
        "shared_company_data_preserved": len(company_ids) - len(safe_company_ids),
        "message": "Your workspace data was reset. Your login account remains active; you can upload your Excel and master resume again.",
    }
