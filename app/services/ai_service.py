import json
from typing import Any

from openai import OpenAI

from app.core.config import settings


class AIService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    def tailor_resume(self, candidate: dict[str, Any], job: dict[str, Any], match: dict[str, Any]) -> dict[str, Any]:
        if not self.client:
            return {
                "summary": candidate.get("resume_text", "")[:600],
                "skills": match.get("evidence", []),
                "projects": [],
                "claims": [],
                "fallback": True,
            }

        prompt = f"""
You are a resume tailoring engine.

NON-NEGOTIABLE:
- Use only facts present in CANDIDATE.
- Never invent technologies, employers, metrics, dates, achievements, or responsibilities.
- You may reorder, shorten, and rewrite existing evidence.
- Preserve factual meaning.
- Optimize for the JOB.
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
  "projects": [
    {{"name": "...", "bullets": ["..."]}}
  ],
  "claims": ["every factual claim used"],
  "removed_sections": ["..."]
}}
"""
        response = self.client.responses.create(
            model=settings.openai_model,
            input=prompt,
        )
        text = response.output_text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("AI returned invalid resume JSON") from exc

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
