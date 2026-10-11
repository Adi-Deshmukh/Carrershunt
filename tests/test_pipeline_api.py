from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, CandidateProfile, Company, Job
from app.db.session import get_db
from app.main import app


def test_analyze_role_endpoint_runs_pipeline_on_persisted_job_and_candidate():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, expire_on_commit=False)

    with test_session() as db:
        company = Company(name="Example", careers_url="https://example.com/careers")
        db.add(company)
        db.flush()
        candidate = CandidateProfile(
            name="Test Candidate",
            resume_text=("Python FastAPI PostgreSQL data engineering machine learning " * 8),
            experience_years=1,
            education="B.Tech Computer Science",
        )
        db.add(candidate)
        db.flush()
        job = Job(
            company_id=company.id,
            title="Junior Data Engineer",
            description=("Build and maintain Python services, SQL data pipelines, and production analytics systems. " * 5),
            job_url="https://example.com/jobs/data-engineer-123",
            apply_url="https://example.com/apply/123",
            source="generic",
        )
        db.add(job)
        db.commit()
        job_id = job.id

    def override_get_db():
        with test_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.post(f"/pipeline/{job_id}?use_llm=false")
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["status"] == "completed"
        assert result["job_id"] == job_id
        assert result["match"]["fit_score"] >= 0
        assert result["resume"] is not None
        assert result["resume_generated"] is False
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(engine)
        engine.dispose()
