from typing import Any

from app.db.models import CandidateProfile, Job
from app.schemas.agent import MatchDecision, ResumePlan, StructuredJob
from app.services.claim_validator import validate_resume_plan
from app.services.evidence import retrieve_evidence
from app.services.eligibility import evaluate_hard_eligibility
from app.services.job_intelligence import parse_job
from app.services.matching import match_job


class AgentService:
    def structure_job(self, job: Job, use_llm: bool = False) -> StructuredJob:
        structured = parse_job(job)
        if use_llm:
            from app.services.job_intelligence import enrich_job_with_llm
            structured = enrich_job_with_llm(job, structured)
        return structured

    def build_candidate_context(self, db, candidate: CandidateProfile, query: str) -> list[dict[str, Any]]:
        return retrieve_evidence(db, candidate.id, query, limit=10)

    def match(
        self,
        db,
        candidate: CandidateProfile,
        job: Job,
        structured: StructuredJob,
    ) -> tuple[MatchDecision, list[dict[str, Any]]]:
        query = " ".join(
            structured.required_skills
            + structured.preferred_skills
            + structured.responsibilities[:5]
        )
        evidence = self.build_candidate_context(db, candidate, query)
        deterministic = match_job(job, candidate)
        eligible, hard_failures = evaluate_hard_eligibility(candidate, job, structured)

        score = deterministic.fit_score
        if evidence:
            evidence_skills = {
                skill.lower()
                for item in evidence
                for skill in item.get("skills", [])
            }
            required = set(structured.required_skills)
            if required:
                score = round(100 * len(required & evidence_skills) / len(required), 1)
        if not eligible:
            score = min(score, 49.0)

        decision = MatchDecision(
            eligible=eligible,
            fit_score=score,
            interview_estimate=(
                "high" if eligible and score >= 85 else
                "moderate-high" if eligible and score >= 70 else
                "moderate" if eligible and score >= 55 else "low"
            ),
            confidence="high" if evidence and structured.required_skills else "medium",
            explanation=(
                f"Evidence-grounded match: {score:.1f}/100. "
                f"Hard eligibility {'passed' if eligible else 'failed'}."
            ),
            hard_failures=hard_failures,
            gaps=[
                skill for skill in structured.required_skills
                if skill.lower() not in {
                    s.lower() for item in evidence for s in item.get("skills", [])
                }
            ],
            evidence=evidence,
        )
        return decision, evidence

    def resume_plan(
        self,
        candidate: CandidateProfile,
        structured: StructuredJob,
        match: MatchDecision,
        evidence: list[dict[str, Any]],
        use_llm: bool = False,
    ) -> tuple[ResumePlan, list[str]]:
        if use_llm:
            from app.services.ai_service import AIService
            plan = AIService().tailor_resume_plan(
                candidate,
                structured,
                match,
                evidence,
            )
        else:
            plan = ResumePlan(
                summary=(
                    f"{candidate.name} with {candidate.experience_years:g} years of experience "
                    f"aligned to {structured.title}."
                ),
                skills=[
                    skill for skill in structured.required_skills
                    if skill.lower() in {
                        s.lower() for item in evidence for s in item.get("skills", [])
                    }
                ],
                projects=[
                    {
                        "name": item["title"],
                        "bullets": [item["content"][:400]],
                    }
                    for item in evidence[:3]
                    if item.get("type") in {"project", "github"}
                ],
                claims=[],
            )
            plan = ResumePlan.model_validate(plan)
        errors = validate_resume_plan(plan, evidence, candidate.resume_text or "")
        return plan, errors
