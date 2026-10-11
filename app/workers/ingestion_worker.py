"""Durable DB-backed ingestion worker.

Run separately from the API:
    python -m app.workers.ingestion_worker --workers 4
Multiple processes can share the same database. Tasks are claimed with a
conditional UPDATE, so two workers cannot own the same queued task.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import socket
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select, update

from app.db.models import (
    Base,
    CandidateProfile,
    Company,
    IngestionRun,
    IngestionTask,
    Job,
)
from app.db.session import SessionLocal, engine
from app.services.job_service import ingest_company_jobs
from app.services.pipeline_service import run_pipeline

MAX_ATTEMPTS = 3
POLL_SECONDS = 1.0
TERMINAL_STATES = {"completed", "failed", "skipped"}


def claim_task(worker_id: str) -> int | None:
    """Atomically claim the oldest queued task; safe across worker processes."""
    with SessionLocal() as db:
        task_id = db.scalar(
            select(IngestionTask.id)
            .where(IngestionTask.status == "queued")
            .order_by(IngestionTask.id)
            .limit(1)
        )
        if task_id is None:
            return None
        now = datetime.utcnow()
        claimed = db.execute(
            update(IngestionTask)
            .where(IngestionTask.id == task_id, IngestionTask.status == "queued")
            .values(
                status="running",
                attempts=IngestionTask.attempts + 1,
                worker_id=worker_id,
                started_at=now,
                updated_at=now,
            )
        )
        if claimed.rowcount != 1:
            db.rollback()
            return None
        db.commit()
        return task_id


def refresh_run_status(db, run_id: int) -> None:
    run = db.get(IngestionRun, run_id)
    if run is None:
        return
    tasks = db.scalars(
        select(IngestionTask).where(IngestionTask.run_id == run_id)
    ).all()
    statuses = [task.status for task in tasks]
    if statuses and all(status in TERMINAL_STATES for status in statuses):
        run.status = "completed" if all(status == "completed" for status in statuses) else "completed_with_errors"
    elif not statuses:
        run.status = "completed"
    else:
        run.status = "running"
    run.updated_at = datetime.utcnow()


async def process_task(task_id: int, worker_id: str) -> None:
    with SessionLocal() as db:
        task = db.get(IngestionTask, task_id)
        if task is None:
            return
        run_id = task.run_id
        try:
            if task.task_type == "scrape_company":
                company = db.get(Company, task.company_id) if task.company_id else None
                if company is None:
                    raise ValueError("Company record no longer exists")
                jobs = await ingest_company_jobs(db, company)
                task.jobs_ingested = len(jobs)

                # Matching is a separate queue task, never part of the upload request.
                candidate = db.scalar(
                    select(CandidateProfile).order_by(CandidateProfile.id.desc())
                )
                if candidate:
                    for job in jobs:
                        db.add(
                            IngestionTask(
                                run_id=run_id,
                                task_type="pipeline_job",
                                job_id=job.id,
                                status="queued",
                            )
                        )
            elif task.task_type == "pipeline_job":
                job = db.get(Job, task.job_id) if task.job_id else None
                candidate = db.scalar(
                    select(CandidateProfile).order_by(CandidateProfile.id.desc())
                )
                if job is None or candidate is None:
                    task.status = "skipped"
                    task.error = "Job or candidate profile unavailable"
                    task.finished_at = datetime.utcnow()
                    db.commit()
                    refresh_run_status(db, run_id)
                    db.commit()
                    return
                run_pipeline(db, candidate, job, use_llm=False)
            else:
                raise ValueError(f"Unsupported ingestion task type: {task.task_type}")

            task.status = "completed"
            task.error = None
            task.finished_at = datetime.utcnow()
            task.updated_at = datetime.utcnow()
            db.commit()
            refresh_run_status(db, run_id)
            db.commit()
        except Exception as exc:
            db.rollback()
            task = db.get(IngestionTask, task_id)
            if task is not None:
                task.error = str(exc)[:2000]
                task.updated_at = datetime.utcnow()
                if task.attempts < MAX_ATTEMPTS:
                    task.status = "queued"
                    task.finished_at = None
                else:
                    task.status = "failed"
                    task.finished_at = datetime.utcnow()
                db.commit()
                refresh_run_status(db, run_id)
                db.commit()


async def worker_loop(worker_id: str) -> None:
    while True:
        task_id = claim_task(worker_id)
        if task_id is None:
            await asyncio.sleep(POLL_SECONDS)
            continue
        await process_task(task_id, worker_id)


async def main(workers: int) -> None:
    Base.metadata.create_all(bind=engine)
    tasks = []
    for index in range(workers):
        worker_id = f"{socket.gethostname()}-{os.getpid()}-{index}-{uuid4().hex[:6]}"
        tasks.append(asyncio.create_task(worker_loop(worker_id)))
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carrershunt durable ingestion workers")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent worker loops")
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 32:
        parser.error("--workers must be between 1 and 32")
    asyncio.run(main(args.workers))
