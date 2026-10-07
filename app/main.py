from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.applications import router as applications_router\nfrom app.api.routes.candidates import router as candidates_router
from app.api.routes.companies import router as companies_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.matches import router as matches_router
from app.api.routes.people import router as people_router
from app.api.routes.resumes import router as resumes_router
from app.db.models import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Carrershunt API",
    version="0.1.0",
    description="Job discovery, matching, resume tailoring, and outreach platform.",
    lifespan=lifespan,
)

app.include_router(candidates_router)\napp.include_router(companies_router)
app.include_router(jobs_router)
app.include_router(matches_router)
app.include_router(resumes_router)
app.include_router(people_router)
app.include_router(applications_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
