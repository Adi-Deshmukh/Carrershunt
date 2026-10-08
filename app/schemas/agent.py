from pydantic import BaseModel, Field


class StructuredJob(BaseModel):
    title: str
    company: str
    location: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    required_years_experience: float = 0
    education_requirements: list[str] = Field(default_factory=list)
    authorization_requirements: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)


class MatchDecision(BaseModel):
    eligible: bool
    fit_score: float = Field(ge=0, le=100)
    interview_estimate: str
    confidence: str
    explanation: str
    hard_failures: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)


class ResumeProject(BaseModel):
    name: str
    bullets: list[str] = Field(default_factory=list)


class ResumePlan(BaseModel):
    summary: str
    skills: list[str] = Field(default_factory=list)
    projects: list[ResumeProject] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)
    removed_sections: list[str] = Field(default_factory=list)


class PipelineResult(BaseModel):
    run_id: int
    candidate_id: int
    job_id: int
    status: str
    job: StructuredJob
    match: MatchDecision
    resume: ResumePlan | None = None
    resume_generated: bool = False
    validation_errors: list[str] = Field(default_factory=list)
