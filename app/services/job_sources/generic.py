from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.services.job_sources.base import JobRecord, JobSource


class GenericSource(JobSource):
    name = "generic"

    async def fetch_jobs(self, careers_url: str) -> list[JobRecord]:
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": "Carrershunt/0.1 (+job-research-tool)"},
        ) as client:
            response = await client.get(careers_url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        jobs = []
        for link in soup.select("a[href]"):
            title = " ".join(link.get_text(" ", strip=True).split())
            href = link.get("href")
            if not href or not title:
                continue
            if any(word in title.lower() for word in ("engineer", "developer", "intern", "analyst", "scientist", "manager")):
                absolute = urljoin(careers_url, href)
                jobs.append(JobRecord(title, None, None, None, title, absolute, absolute, self.name, None))
        return list({job.job_url: job for job in jobs}.values())
