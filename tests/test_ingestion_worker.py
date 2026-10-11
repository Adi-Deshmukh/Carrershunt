from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Company, IngestionRun, IngestionTask
from app.workers import ingestion_worker


def test_workers_claim_distinct_queued_tasks(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(ingestion_worker, "SessionLocal", session_factory)

    with session_factory() as db:
        company = Company(name="Example", careers_url="https://example.com/careers")
        db.add(company)
        db.flush()
        run = IngestionRun(total_companies=3, status="queued")
        db.add(run)
        db.flush()
        db.add_all([
            IngestionTask(run_id=run.id, task_type="scrape_company", company_id=company.id),
            IngestionTask(run_id=run.id, task_type="scrape_company", company_id=company.id),
            IngestionTask(run_id=run.id, task_type="scrape_company", company_id=company.id),
        ])
        db.commit()
        run_id = run.id

    first = ingestion_worker.claim_task("worker-a")
    second = ingestion_worker.claim_task("worker-b")
    third = ingestion_worker.claim_task("worker-c")

    assert first is not None
    assert second is not None
    assert third is not None
    assert len({first, second, third}) == 3

    with session_factory() as db:
        tasks = db.scalars(
            select(IngestionTask).where(IngestionTask.run_id == run_id).order_by(IngestionTask.id)
        ).all()
        run = db.get(IngestionRun, run_id)
        assert [task.status for task in tasks] == ["running", "running", "running"]
        assert [task.attempts for task in tasks] == [1, 1, 1]
        assert run.status == "running"
