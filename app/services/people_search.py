import httpx

from app.core.config import settings
from app.services.people_service import PersonCandidate


class SerperPeopleProvider:
    async def search(self, company: str, role: str, skills: list[str]) -> list[PersonCandidate]:
        if not settings.serper_api_key:
            return []

        query = f'site:linkedin.com/in "{company}" ("{role}" OR engineer OR recruiter) ' + " ".join(skills[:4])
        headers = {"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://google.serper.dev/search",
                headers=headers,
                json={"q": query, "num": 10},
            )
            response.raise_for_status()
            payload = response.json()

        results = []
        for item in payload.get("organic", []):
            link = item.get("link", "")
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            if "linkedin.com/in/" not in link:
                continue

            score = 50.0
            lowered = f"{title} {snippet}".lower()
            if "recruit" in lowered:
                score += 15
            if "manager" in lowered:
                score += 15
            if any(skill.lower() in lowered for skill in skills):
                score += 10

            results.append(
                PersonCandidate(
                    name=title.split(" - ")[0].strip(),
                    role=snippet[:300],
                    profile_url=link,
                    relevance_score=min(score, 100),
                    rationale="Found through public search results; ranking based on role and skill overlap.",
                )
            )

        return sorted(results, key=lambda x: x.relevance_score, reverse=True)
