from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, Company, IngestionRun, IngestionTask
from app.db.session import get_db
from app.main import app


def test_manual_ingest_endpoint_only_queues_work():
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
        db.commit()
        company_id = company.id

    def override_get_db():
        with test_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.post(f"/jobs/ingest/company/{company_id}")

        assert response.status_code == 202
        payload = response.json()
        assert payload["status"] == "queued"
        assert payload["ingestion_run_id"] is not None

        with test_session() as db:
            run = db.get(IngestionRun, payload["ingestion_run_id"])
            tasks = db.scalars(
                select(IngestionTask).where(IngestionTask.run_id == payload["ingestion_run_id"])
            ).all()
            assert run is not None
            assert run.status == "queued"
            assert len(tasks) == 1
            assert tasks[0].task_type == "scrape_company"
            assert tasks[0].status == "queued"
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(engine)
        engine.dispose()
