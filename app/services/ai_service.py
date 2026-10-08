import json
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.schemas.agent import ResumePlan, StructuredJob


class AIService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    def _json(self, prompt: str) -> dict[str, Any]:
        if not self.client:
            raise RuntimeError("OpenAI API is not configured")
        response = self.client.responses.create(model=settings.openai_model, input=prompt)
        text = response.output_text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("AI returned invalid JSON") from exc

    def structure_job(self, job: dict[str, Any], baseline: dict[str, Any]) -> StructuredJob:
        if not self.client:
            return StructuredJob.model_validate(baseline)

        prompt = (
            "Extract a job description into the supplied schema. Do not invent requirements. "
            "Use only information explicitly supported by the job. Return JSON only.\n\n"
            f"JOB:\n{json.dumps(job, ensure_ascii=False)}\n\n"
            f"BASELINE:\n{json.dumps(baseline, ensure_ascii=False)}\n\n"
            "Schema keys: title, company, location, employment_type, seniority, required_skills, "
            "preferred_skills, required_years_experience, education_requirements, "
            "authorization_requirements, responsibilities, qualifications."
        )
        return StructuredJob.model_validate(self._json(prompt))

    def tailor_resume(
        self,
        candidate: dict[str, Any],
        job: dict[str, Any],
        match: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.client:
            return {
                "summary": candidate.get("resume_text", "")[:600],
                "skills": match.get("evidence", []),
                "projects": [],
                "claims": [],
                "removed_sections": [],
                "fallback": True,
            }

        prompt = f"""
You are a resume tailoring engine.

NON-NEGOTIABLE:
- Use only facts present in CANDIDATE and EVIDENCE.
- Never invent technologies, employers, metrics, dates, achievements, or responsibilities.
- Reorder, shorten, and rewrite existing evidence only.
- Optimize for JOB.
- Return JSON only.

CANDIDATE:
{json.dumps(candidate, ensure_ascii=False)}

JOB:
{json.dumps(job, ensure_ascii=False)}

MATCH:
{json.dumps(match, ensure_ascii=False)}

Return:
{{
  "summary": "...",
  "skills": ["..."],
  "projects": [{{"name": "...", "bullets": ["..."]}}],
  "claims": ["every factual claim used"],
  "removed_sections": ["..."]
}}
"""
        return self._json(prompt)

    def tailor_resume_plan(
        self,
        candidate,
        structured: StructuredJob,
        match,
        evidence: list[dict[str, Any]],
    ) -> ResumePlan:
        candidate_payload = {
            "name": candidate.name,
            "education": candidate.education,
            "experience_years": candidate.experience_years,
            "resume_text": candidate.resume_text,
        }
        result = self.tailor_resume(
            candidate_payload,
            structured.model_dump(),
            match.model_dump(),
        )
        return ResumePlan.model_validate(result)

    def explain_match(self, job: dict[str, Any], candidate: dict[str, Any], match: dict[str, Any]) -> str:
        if not self.client:
            return match["explanation"]

        response = self.client.responses.create(
            model=settings.openai_model,
            input=(
                "Explain this job match in 120 words or fewer. Be factual, direct, and do not "
                "invent evidence.\n\n"
                + json.dumps({"job": job, "candidate": candidate, "match": match}, ensure_ascii=False)
            ),
        )
        return response.output_text.strip()
