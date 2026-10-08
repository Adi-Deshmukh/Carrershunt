from typing import Any

from app.db.models import CandidateProfile, Job
from app.schemas.agent import MatchDecision, ResumePlan, StructuredJob
from app.services.claim_validator import validate_resume_plan
from app.services.evidence import retrieve_evidence
from app.services.eligibility import evaluate_hard_eligibility
from app.services.job_intelligence import SKILLS, _contains, parse_job
from app.services.matching import match_job
from app.services.semantic_match import hybrid_match_score


class AgentService:
    def structure_job(self, job: Job, use_llm: bool = False) -> StructuredJob:
        structured = parse_job(job)
        if use_llm:
            from app.services.job_intelligence import enrich_job_with_llm
            structured = enrich_job_with_llm(job, structured)
        return structured

    def build_candidate_context(self, db, candidate: CandidateProfile, query: str) -> list[dict[str, Any]]:
        return retrieve_evidence(db, candidate.id, query, limit=10)

    def match(self, db, candidate: CandidateProfile, job: Job, structured: StructuredJob) -> tuple[MatchDecision, list[dict[str, Any]]]:
        query = " ".join(structured.required_skills + structured.preferred_skills + structured.responsibilities[:5])
        evidence = self.build_candidate_context(db, candidate, query)
        deterministic = match_job(job, candidate)
        eligible, hard_failures = evaluate_hard_eligibility(candidate, job, structured)
        evidence_skills = {skill.lower() for item in evidence for skill in item.get("skills", [])}
        candidate_text = " ".join([candidate.resume_text or ""] + [item.get("content", "") for item in evidence])
        semantic = hybrid_match_score(
            structured.required_skills,
            structured.preferred_skills,
            job.description or job.title,
            candidate_text,
            evidence_skills,
        )
        score = semantic["score"] if structured.required_skills else deterministic.fit_score
        if not eligible:
            score = min(score, 49.0)
        confidence = "high" if evidence and structured.required_skills else "medium"
        decision = MatchDecision(
            eligible=eligible,
            fit_score=score,
            interview_estimate=("high" if eligible and score >= 85 else "moderate-high" if eligible and score >= 70 else "moderate" if eligible and score >= 55 else "low"),
            confidence=confidence,
            explanation=(f"Hybrid match: {score:.1f}/100; required-skill coverage={semantic['required_skill_coverage']:.0%}; "
                         f"semantic similarity={semantic['semantic_similarity']:.0%}. "
                         f"Hard eligibility {'passed' if eligible else 'failed'}.") ,
            hard_failures=hard_failures,
            gaps=semantic["gaps"],
            evidence=evidence,
            score_breakdown={
                "required_skill_coverage": semantic["required_skill_coverage"],
                "preferred_skill_coverage": semantic["preferred_skill_coverage"],
                "semantic_similarity": semantic["semantic_similarity"],
            },
        )
        return decision, evidence

    def resume_plan(self, candidate: CandidateProfile, structured: StructuredJob, match: MatchDecision, evidence: list[dict[str, Any]], use_llm: bool = False) -> tuple[ResumePlan, list[str]]:
        if use_llm:
            from app.services.ai_service import AIService
            plan = AIService().tailor_resume_plan(candidate, structured, match, evidence)
        else:
            matched = {s.lower() for item in evidence for s in item.get("skills", [])}
            candidate_text = (candidate.resume_text or "").lower()
            grounded_skills = []
            for skill in structured.required_skills:
                skill_lower = skill.lower()
                if skill_lower in matched or skill_lower in candidate_text:
                    grounded_skills.append(skill)
            for skill in structured.preferred_skills:
                skill_lower = skill.lower()
                if skill_lower in matched or skill_lower in candidate_text:
                    if skill not in grounded_skills:
                        grounded_skills.append(skill)
            # If the JD has few/no recognized skills, retain verified candidate
            # skills so a valid resume does not collapse into summary-only output.
            for skill in SKILLS:
                if len(grounded_skills) >= 12:
                    break
                if _contains(candidate.resume_text or "", skill) and skill not in grounded_skills:
                    grounded_skills.append(skill)
            plan = ResumePlan(
                summary=f"{candidate.name} with {candidate.experience_years:g} years of experience aligned to {structured.title}.",
                skills=grounded_skills,
                projects=[{"name": item["title"], "bullets": [item["content"][:400]]} for item in evidence[:3] if item.get("type") in {"project", "github"}],
                claims=[],
            )
            plan = ResumePlan.model_validate(plan)
        errors = validate_resume_plan(plan, evidence, candidate.resume_text or "")
        return plan, errors
