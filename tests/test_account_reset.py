from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes.account import reset_account_workspace
from app.db.models import (
    Base,
    CandidateProfile,
    Company,
    IngestionRun,
    IngestionTask,
    Job,
    PipelineRun,
)


def make_db() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine, expire_on_commit=False)


def add_company(db: Session, name: str, owner_id: str) -> tuple[Company, Job]:
    company = Company(name=name, careers_url=f"https://{name.lower()}.example/careers")
    db.add(company)
    db.flush()
    job = Job(
        company_id=company.id,
        title="Software Engineer",
        description="Build and maintain production software systems. " * 5,
        job_url=f"https://{name.lower()}.example/jobs/software-engineer",
        apply_url=f"https://{name.lower()}.example/jobs/software-engineer",
        source="generic",
        status="open",
    )
    db.add(job)
    db.flush()
    run = IngestionRun(total_companies=1, status="completed", supabase_user_id=owner_id)
    db.add(run)
    db.flush()
    db.add(IngestionTask(run_id=run.id, company_id=company.id, status="completed"))
    db.flush()
    return company, job


def test_reset_removes_account_candidate_and_unshared_imported_jobs():
    db = make_db()
    try:
        company, job = add_company(db, "Example", "user-a")
        candidate = CandidateProfile(
            supabase_user_id="user-a",
            name="Candidate A",
            resume_text="Master resume text " * 10,
        )
        db.add(candidate)
        db.flush()
        db.add(PipelineRun(candidate_id=candidate.id, job_id=job.id, status="completed", result_json="{}"))
        db.commit()
        company_id, job_id, candidate_id = company.id, job.id, candidate.id

        result = reset_account_workspace(db, {"id": "user-a"})

        assert result["status"] == "reset"
        assert result["companies_removed"] == 1
        assert result["jobs_removed"] == 1
        assert db.get(Company, company_id) is None
        assert db.get(Job, job_id) is None
        assert db.get(CandidateProfile, candidate_id) is None
    finally:
        db.close()


def test_reset_preserves_company_referenced_by_another_signed_in_account():
    db = make_db()
    try:
        company = Company(name="Shared", careers_url="https://shared.example/careers")
        db.add(company)
        db.flush()
        job = Job(
            company_id=company.id,
            title="Data Engineer",
            description="Build and maintain production data pipelines. " * 5,
            job_url="https://shared.example/jobs/data-engineer",
            apply_url="https://shared.example/jobs/data-engineer",
            source="generic",
            status="open",
        )
        db.add(job)
        db.flush()
        run_a = IngestionRun(total_companies=1, status="completed", supabase_user_id="user-a")
        run_b = IngestionRun(total_companies=1, status="completed", supabase_user_id="user-b")
        db.add_all([run_a, run_b])
        db.flush()
        db.add_all([
            IngestionTask(run_id=run_a.id, company_id=company.id, status="completed"),
            IngestionTask(run_id=run_b.id, company_id=company.id, status="completed"),
        ])
        db.commit()
        company_id, job_id = company.id, job.id

        result = reset_account_workspace(db, {"id": "user-a"})

        assert result["shared_company_data_preserved"] == 1
        assert db.get(Company, company_id) is not None
        assert db.get(Job, job_id) is not None
        remaining_runs = db.scalars(select(IngestionRun)).all()
        assert len(remaining_runs) == 1
        assert remaining_runs[0].supabase_user_id == "user-b"
    finally:
        db.close()
