from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

APP_VERSION = "0.2.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


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

app.include_router(candidates_router)
app.include_router(companies_router)
app.include_router(jobs_router)
app.include_router(matches_router)
app.include_router(resumes_router)
app.include_router(people_router)
app.include_router(applications_router)
app.include_router(evidence_router)
app.include_router(github_router)
app.include_router(resume_ingestion_router)
app.include_router(pipeline_router)
app.include_router(settings_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
