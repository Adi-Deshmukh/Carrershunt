from pydantic import BaseModel, Field


class EvidenceSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=8, ge=1, le=50)
    evidence_type: str | None = None


class GitHubSyncRequest(BaseModel):
    username_or_url: str = Field(min_length=1, max_length=300)
    max_repos: int = Field(default=25, ge=1, le=100)
