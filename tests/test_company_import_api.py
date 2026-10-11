from io import BytesIO

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import select, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, IngestionRun, IngestionTask
from app.db.session import get_db
from app.main import app


def test_excel_import_queues_scraping_without_waiting_for_it():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        with test_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        workbook = BytesIO()
        pd.DataFrame(
            [{"Company": "Example Co", "Careers URL": "https://example.com/jobs"}]
        ).to_excel(workbook, index=False)

        with TestClient(app) as client:
            response = client.post(
                "/companies/import",
                files={
                    "file": (
                        "companies.xlsx",
                        workbook.getvalue(),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )

        assert response.status_code == 202
        payload = response.json()
        assert payload["queued_companies"] == 1
        assert payload["jobs_ingested"] == 0
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
