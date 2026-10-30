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
        # Pulling a few broad project records as well as top lexical matches keeps
        # GitHub evidence discoverable when the JD uses a synonym or different wording.
        focused = retrieve_evidence(db, candidate.id, query, limit=10)
        projects = retrieve_evidence(db, candidate.id, "", limit=50, evidence_type="project")
        by_id = {item["id"]: item for item in focused}
        for item in projects:
            by_id.setdefault(item["id"], item)
        return list(by_id.values())[:50]

    def match(self, db, candidate: CandidateProfile, job: Job, structured: StructuredJob) -> tuple[MatchDecision, list[dict[str, Any]]]:
        query = " ".join(structured.required_skills + structured.preferred_skills + structured.responsibilities[:5])
        evidence = self.build_candidate_context(db, candidate, query)
        deterministic = match_job(job, candidate)
        eligible, hard_failures = evaluate_hard_eligibility(candidate, job, structured)
        evidence_skills = {
            skill.lower()
            for item in evidence
            for skill in item.get("skills", [])
        }
        candidate_text = " ".join(
            [candidate.resume_text or "", candidate.education or ""]
            + [item.get("content", "") for item in evidence]
        )
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
        confidence = "medium"
        if evidence and structured.required_skills:
            confidence = "high" if any(item.get("source") == "github" for item in evidence) else "medium"
        decision = MatchDecision(
            eligible=eligible,
            fit_score=score,
            interview_estimate=("high" if eligible and score >= 85 else "moderate-high" if eligible and score >= 70 else "moderate" if eligible and score >= 55 else "low"),
            confidence=confidence,
            explanation=(
                f"Evidence-based fit: {score:.1f}/100; "
                f"required-skill coverage={semantic['required_skill_coverage']:.0%}; "
                f"preferred-skill coverage={semantic['preferred_skill_coverage']:.0%}; "
                f"text similarity={semantic['semantic_similarity']:.0%}. "
                f"Hard eligibility {'passed' if eligible else 'failed'}."
            ),
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
            available_skills = {
                str(skill).strip().lower()
                for item in evidence
                for skill in item.get("skills", [])
            }
            candidate_text = (candidate.resume_text or "").lower()
            grounded_skills = []
            for skill in structured.required_skills + structured.preferred_skills:
                if skill.lower() in available_skills or _contains(candidate.resume_text or "", skill):
                    if skill not in grounded_skills:
                        grounded_skills.append(skill)
            for skill in SKILLS:
                if len(grounded_skills) >= 15:
                    break
                if (_contains(candidate.resume_text or "", skill) or skill.lower() in available_skills) and skill not in grounded_skills:
                    grounded_skills.append(skill)

            # Repository evidence is summarized into resume bullets only when it
            # includes a concise, factual project description. Keep the originating
            # evidence text intact so the claim validator can reject unsupported edits.
            project_items = [
                item for item in evidence
                if item.get("type") == "project" and item.get("content")
            ]
            projects = [
                {"name": item["title"], "bullets": [item["content"][:350]]}
                for item in project_items[:4]
            ]
            plan = ResumePlan(
                summary=f"{candidate.name} focused on {structured.title} with {candidate.experience_years:g} years of experience.",
                skills=grounded_skills,
                projects=projects,
                claims=[],
            )
            plan = ResumePlan.model_validate(plan)
        errors = validate_resume_plan(plan, evidence, candidate.resume_text or "")
        return plan, errors
