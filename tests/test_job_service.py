import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes.candidates import get_latest_candidate
from app.db.models import Base, CandidateProfile, Company, Job
from app.services import job_service
from app.services.job_sources.base import JobRecord


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_latest_candidate_is_scoped_to_authenticated_user():
    db = make_db()
    db.add_all([
        CandidateProfile(name="Account A", supabase_user_id="user-a", resume_text="A" * 150),
        CandidateProfile(name="Account B", supabase_user_id="user-b", resume_text="B" * 150),
    ])
    db.commit()

    result = get_latest_candidate(db, {"id": "user-a"})

    assert result["name"] == "Account A"


def test_ingestion_discards_careers_index_and_short_placeholder_rows(monkeypatch):
    db = make_db()
    company = Company(name="Example", careers_url="https://example.com/careers")
    db.add(company)
    db.flush()

    class FakeSource:
        async def fetch_jobs(self, careers_url):
            return [
                JobRecord(
                    title="Fake index row",
                    location=None,
                    employment_type=None,
                    department=None,
                    description="Fake index row",
                    job_url=careers_url,
                    apply_url=careers_url,
                    source="generic",
                    source_job_id=None,
                ),
                JobRecord(
                    title="Data Engineer",
                    location="Remote",
                    employment_type="Full-time",
                    department="Engineering",
                    description="Build and operate production data pipelines. " * 8,
                    job_url="https://example.com/jobs/data-engineer-123",
                    apply_url="https://example.com/apply/123",
                    source="generic",
                    source_job_id="123",
                ),
            ]

    monkeypatch.setattr(job_service, "get_source", lambda platform: FakeSource())
    stored = asyncio.run(job_service.ingest_company_jobs(db, company))

    assert len(stored) == 1
    assert stored[0].title == "Data Engineer"
    assert stored[0].job_url == "https://example.com/jobs/data-engineer-123"
    assert stored[0].apply_url == "https://example.com/apply/123"
    assert len(stored[0].description) >= 100
