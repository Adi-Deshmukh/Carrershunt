from pydantic import BaseModel, Field


class CandidateUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    education: str | None = None
    graduation_year: int | None = None
    experience_years: float | None = None
    location: str | None = None
    work_authorization: str | None = None


class CandidateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str | None = None
    education: str | None = None
    graduation_year: int | None = None
    experience_years: float = 0
    location: str | None = None
    work_authorization: str | None = None
    resume_text: str
    evidence: dict = Field(default_factory=dict)
