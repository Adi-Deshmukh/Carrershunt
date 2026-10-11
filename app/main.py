import asyncio
import logging
import os
import socket
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.account import router as account_router
from app.api.routes.applications import router as applications_router
from app.api.routes.candidates import router as candidates_router
from app.api.routes.companies import router as companies_router
from app.api.routes.evidence import router as evidence_router
from app.api.routes.github import router as github_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.matches import router as matches_router
from app.api.routes.people import router as people_router
from app.api.routes.pipeline import router as pipeline_router
from app.api.routes.resume_ingestion import router as resume_ingestion_router
from app.api.routes.resumes import router as resumes_router
from app.api.routes.settings import router as settings_router
from app.db.models import Base
from app.db.session import engine
from app.db.migrations import ensure_schema_compatibility
from app.core.auth import get_current_user
from app.workers.ingestion_worker import worker_loop

APP_VERSION = "0.2.0"
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility(engine)

    worker_tasks = []
    worker_enabled = os.getenv("ENABLE_INGESTION_WORKER", "true").strip().lower() not in {
        "0", "false", "no", "off",
    }
    if worker_enabled:
        try:
            worker_count = int(os.getenv("INGESTION_WORKERS", "4"))
        except ValueError as exc:
            raise RuntimeError("INGESTION_WORKERS must be an integer between 1 and 32") from exc
        if not 1 <= worker_count <= 32:
            raise RuntimeError("INGESTION_WORKERS must be between 1 and 32")

        for index in range(worker_count):
            worker_id = f"{socket.gethostname()}-{os.getpid()}-api-{index}-{uuid4().hex[:6]}"
            worker_tasks.append(
                asyncio.create_task(worker_loop(worker_id), name=f"ingestion-worker-{index}")
            )
        logger.info("Started %s ingestion worker(s) with the API process", worker_count)
    else:
        logger.info("In-process ingestion workers disabled by configuration")

    try:
        yield
    finally:
        for task in worker_tasks:
            task.cancel()
        if worker_tasks:
            await asyncio.gather(*worker_tasks, return_exceptions=True)
        logger.info("Stopped in-process ingestion workers")


app = FastAPI(
    title="Carrershunt API",
    version=APP_VERSION,
    description="Job discovery, candidate intelligence, matching, resume tailoring, outreach, and application tracking.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(candidates_router, dependencies=[Depends(get_current_user)])
app.include_router(companies_router, dependencies=[Depends(get_current_user)])
app.include_router(jobs_router, dependencies=[Depends(get_current_user)])
app.include_router(matches_router, dependencies=[Depends(get_current_user)])
app.include_router(resumes_router, dependencies=[Depends(get_current_user)])
app.include_router(people_router, dependencies=[Depends(get_current_user)])
app.include_router(account_router, dependencies=[Depends(get_current_user)])
app.include_router(applications_router, dependencies=[Depends(get_current_user)])
app.include_router(evidence_router, dependencies=[Depends(get_current_user)])
app.include_router(github_router, dependencies=[Depends(get_current_user)])
app.include_router(resume_ingestion_router, dependencies=[Depends(get_current_user)])
app.include_router(pipeline_router, dependencies=[Depends(get_current_user)])
app.include_router(settings_router, dependencies=[Depends(get_current_user)])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
