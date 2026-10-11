import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, CandidateEvidence, CandidateProfile, Company, Job, PipelineRun
from app.db.session import get_db
from app.main import app


def test_tailor_resume_accepts_numeric_claims_grounded_in_indexed_evidence(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, expire_on_commit=False)

    plan = {
        "summary": "Test Candidate is a Data Engineer focused on Python data pipelines and reliable backend services.",
        "skills": ["Python", "SQL"],
        "projects": [
            {
                "name": "Data ingestion project",
                "bullets": ["Processed 12,000 records with a Python ingestion pipeline."],
            }
        ],
        "claims": [],
        "removed_sections": [],
    }

    with test_session() as db:
        company = Company(name="Example", careers_url="https://example.com/careers")
        db.add(company)
        db.flush()
        candidate = CandidateProfile(
            name="Test Candidate",
            resume_text="Python SQL backend services data engineering " * 5,
            experience_years=0,
            education="B.Tech",
            evidence_json="{}",
        )
        db.add(candidate)
        db.flush()
        job = Job(
            company_id=company.id,
            title="Data Engineer",
            description="Build Python data pipelines and reliable backend services. " * 4,
            job_url="https://example.com/jobs/data-engineer",
            source="generic",
        )
        db.add(job)
        db.flush()
        db.add(
            CandidateEvidence(
                candidate_id=candidate.id,
                source="github",
                source_key="example/project",
                evidence_type="project",
                title="Data ingestion project",
                content="Processed 12,000 records with a Python ingestion pipeline.",
                url="https://github.com/example/project",
                metadata_json="{}",
                fingerprint="a" * 64,
            )
        )
        db.add(
            PipelineRun(
                candidate_id=candidate.id,
                job_id=job.id,
                status="completed",
                result_json=json.dumps({"resume": plan}),
            )
        )
        db.commit()
        job_id = job.id

    def override_get_db():
        with test_session() as db:
            yield db

    monkeypatch.setattr(
        "app.api.routes.resumes.generate_docx_from_plan",
        lambda candidate, job, resume_plan: (Path("fake_resume.docx"), resume_plan.model_dump()),
    )
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.post(f"/resumes/tailor/{job_id}")
        assert response.status_code == 200, response.text
        assert response.json()["filename"] == "fake_resume.docx"
        assert response.json()["content"]["projects"][0]["bullets"][0].startswith("Processed 12,000")
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(engine)
        engine.dispose()
