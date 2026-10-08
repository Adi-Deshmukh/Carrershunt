from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.services.job_sources.base import JobRecord, JobSource


JOB_WORDS = (
    "engineer", "developer", "intern", "analyst", "scientist", "manager",
    "designer", "researcher", "product", "security", "data", "machine learning",
)


def _clean(value: str | None) -> str:
    return " ".join((value or "").split())


def _looks_like_job(title: str, url: str) -> bool:
    text = f"{title} {url}".lower()
    return any(word in text for word in JOB_WORDS)


class GenericSource(JobSource):
    name = "generic"

    async def fetch_jobs(self, careers_url: str) -> list[JobRecord]:
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/140 Safari/537.36 "
                    "Carrershunt/0.2"
                )
            },
        ) as client:
            response = await client.get(careers_url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        jobs: dict[str, JobRecord] = {}

        # Prefer schema.org JobPosting data when the careers page exposes it.
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                import json
                payload = json.loads(script.string or script.get_text())
            except (TypeError, ValueError):
                continue

            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                if not isinstance(item, dict) or item.get("@type") != "JobPosting":
                    continue
                title = _clean(item.get("title"))
                url = item.get("url") or careers_url
                if not title:
                    continue
                location = None
                locations = item.get("jobLocation")
                if isinstance(locations, dict):
                    locations = [locations]
                if isinstance(locations, list):
                    values = []
                    for loc in locations:
                        address = loc.get("address", {}) if isinstance(loc, dict) else {}
                        if isinstance(address, dict):
                            values.append(_clean(address.get("addressLocality")))
                    location = ", ".join(x for x in values if x) or None
                jobs[url] = JobRecord(
                    title, location, item.get("employmentType"), None,
                    _clean(item.get("description")), url, url, self.name, None,
                )

        # Fall back to job-like links for ordinary/static careers pages.
        for link in soup.select("a[href]"):
            title = _clean(link.get_text(" ", strip=True))
            href = link.get("href")
            if not href or not title:
                continue
            absolute = urljoin(careers_url, href)
            if _looks_like_job(title, absolute):
                jobs.setdefault(
                    absolute,
                    JobRecord(
                        title, None, None, None, title,
                        absolute, absolute, self.name, None,
                    ),
                )

        return list(jobs.values())
