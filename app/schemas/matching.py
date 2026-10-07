from pydantic import BaseModel


class MatchResult(BaseModel):
    job_id: int
    eligible: bool
    fit_score: float
    interview_estimate: str
    confidence: str
    explanation: str
    gaps: list[str]
    evidence: list[str]
