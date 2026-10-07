from pydantic import BaseModel, Field, HttpUrl


class JobRead(BaseModel):
    id: int
    company_id: int
    title: str
    location: str | None = None
    employment_type: str | None = None
    department: str | None = None
    description: str
    job_url: HttpUrl
    apply_url: HttpUrl | None = None
    source: str
    source_job_id: str | None = None
