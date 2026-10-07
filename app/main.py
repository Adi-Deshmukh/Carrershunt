from fastapi import FastAPI

app = FastAPI(
    title="Carrershunt API",
    version="0.1.0",
    description="Job discovery, matching, resume tailoring, and outreach platform.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
