from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, CandidateProfile, Company, Job
from app.services.pipeline_service import run_pipeline


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_phase2_pipeline_is_end_to_end():
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

    result = run_pipeline(db, candidate, job, use_llm=False)

    assert result.status in {"completed", "completed_with_warnings"}
    assert result.match.eligible is True
    assert result.match.fit_score > 0
    assert result.resume is not None
    assert result.validation_errors == []
