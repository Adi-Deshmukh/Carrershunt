from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, CandidateProfile, Company, Job
from app.services.job_intelligence import parse_job
from app.services.pipeline_service import run_pipeline


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def make_fixture():
    db = make_db()
    company = Company(name="Example", careers_url="https://example.com/careers")
    db.add(company)
    db.flush()

    candidate = CandidateProfile(
        name="Test Candidate",
        experience_years=1,
        education="B.Tech Computer Science",
        resume_text="Python FastAPI PostgreSQL machine learning",
    )
    db.add(candidate)
    db.flush()

    job = Job(
        company_id=company.id,
        title="Junior Python Engineer",
        location="Remote",
        description=(
            "We need Python FastAPI PostgreSQL. "
            "Bachelor degree preferred. 1+ years experience."
        ),
        job_url="https://example.com/jobs/1",
        source="generic",
    )
    db.add(job)
    db.commit()
    return db, candidate, job


def test_phase2_pipeline_is_end_to_end():
    db, candidate, job = make_fixture()

    result = run_pipeline(db, candidate, job, use_llm=False)

    assert result.status == "completed"
    assert result.match.eligible is True
    assert result.match.fit_score > 0
    assert result.resume is not None
    assert result.resume_generated is True
    assert result.resume_id is not None
    assert result.resume_download_url == f"/resumes/{result.resume_id}/download"
    assert result.validation_errors == []


def test_preferred_degree_is_not_a_hard_failure():
    db, candidate, job = make_fixture()

    structured = parse_job(job)

    assert structured.education_requirements == []
    assert candidate.education == "B.Tech Computer Science"
