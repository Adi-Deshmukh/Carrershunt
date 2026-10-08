from app.schemas.agent import ResumePlan, ResumeProject
from app.services.resume_quality import validate_resume_quality


def test_resume_quality_accepts_grounded_plan():
    plan = ResumePlan(summary="Python engineer with 2 years of experience building backend services.", skills=["Python", "FastAPI"], projects=[ResumeProject(name="Fleet API", bullets=["Built a Python FastAPI service for internal workflows."])], claims=[])
    assert validate_resume_quality(plan, "Python FastAPI 2 years experience", "Python Engineer") == []


def test_resume_quality_rejects_new_numbers():
    plan = ResumePlan(summary="Python engineer with 2 years of experience building backend services.", skills=["Python"], projects=[ResumeProject(name="Fleet API", bullets=["Improved latency by 99%."])], claims=[])
    errors = validate_resume_quality(plan, "Python FastAPI 2 years experience", "Python Engineer")
    assert any("unsupported numeric claim" in error.lower() for error in errors)
