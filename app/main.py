from fastapi import FastAPI

from app.api.routes.companies import router as companies_router

app = FastAPI(
    title="Carrershunt API",
    version="0.1.0",
    description="Job discovery, matching, resume tailoring, and outreach platform.",
)

app.include_router(companies_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
