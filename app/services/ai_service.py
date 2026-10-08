import json
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.schemas.agent import ResumePlan, StructuredJob


class AIService:
    """Provider-neutral AI gateway with ordered fallback."""

    _SUPPORTED = ("gemini", "grok", "openai")

    def __init__(self) -> None:
        self.providers = self._build_providers()

    def _build_providers(self) -> dict[str, OpenAI]:
        providers: dict[str, OpenAI] = {}
        if settings.gemini_api_key:
            providers["gemini"] = OpenAI(
                api_key=settings.gemini_api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )
        if settings.xai_api_key:
            providers["grok"] = OpenAI(
                api_key=settings.xai_api_key,
                base_url="https://api.x.ai/v1",
            )
        if settings.openai_api_key:
            providers["openai"] = OpenAI(api_key=settings.openai_api_key)
        return providers

    def configured_providers(self) -> list[str]:
        return list(self.providers)

    def provider_order(self) -> list[str]:
        if settings.ai_provider != "auto":
            requested = [settings.ai_provider]
            if settings.ai_fallback_enabled:
                requested.extend(
                    provider
                    for provider in (settings.ai_primary_provider, *self._SUPPORTED)
                    if provider != settings.ai_provider
                )
        else:
            requested = [settings.ai_primary_provider, *self._SUPPORTED]
        return [p for p in dict.fromkeys(requested) if p in self.providers]

    def _model_for(self, provider: str) -> str:
        return {
            "gemini": settings.gemini_model,
            "grok": settings.xai_model,
            "openai": settings.openai_model,
        }[provider]

    def _json(self, prompt: str) -> dict[str, Any]:
        if not self.providers:
            raise RuntimeError("No AI provider is configured")

        errors: list[str] = []
        for provider in self.provider_order():
            try:
                response = self.providers[provider].chat.completions.create(
                    model=self._model_for(provider),
                    messages=[
                        {"role": "system", "content": "Return valid JSON only. Never invent facts."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0,
                )
                output = (response.choices[0].message.content or "").strip()
                if output.startswith("```"):
                    output = output.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                return json.loads(output)
            except Exception as exc:
                errors.append(f"{provider}: {exc}")

        raise RuntimeError("All configured AI providers failed: " + " | ".join(errors))

    def _text(self, prompt: str, max_words: int = 120) -> str:
        if not self.providers:
            raise RuntimeError("No AI provider is configured")

        errors: list[str] = []
        for provider in self.provider_order():
            try:
                response = self.providers[provider].chat.completions.create(
                    model=self._model_for(provider),
                    messages=[
                        {
                            "role": "system",
                            "content": f"Be factual and direct. Stay within {max_words} words.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0,
                )
                return (response.choices[0].message.content or "").strip()
            except Exception as exc:
                errors.append(f"{provider}: {exc}")

        raise RuntimeError("All configured AI providers failed: " + " | ".join(errors))

    def structure_job(self, job: dict[str, Any], baseline: dict[str, Any]) -> StructuredJob:
        if not self.providers:
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
        if not self.providers:
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
            "evidence": evidence,
        }
        result = self.tailor_resume(
            candidate_payload,
            structured.model_dump(),
            match.model_dump(),
        )
        return ResumePlan.model_validate(result)

    def explain_match(
        self,
        job: dict[str, Any],
        candidate: dict[str, Any],
        match: dict[str, Any],
    ) -> str:
        if not self.providers:
            return match["explanation"]

        return self._text(
            "Explain this job match in 120 words or fewer. Be factual, direct, and do not "
            "invent evidence.\n\n"
            + json.dumps({"job": job, "candidate": candidate, "match": match}, ensure_ascii=False)
        )
