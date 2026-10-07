from bs4 import BeautifulSoup
import httpx

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
        jobs: list[JobRecord] = []

        for link in soup.select("a[href]"):
            title = " ".join(link.get_text(" ", strip=True).split())
            href = link.get("href")
            if not href or not title:
                continue
            lower = title.lower()
            if any(word in lower for word in ("engineer", "developer", "intern", "analyst", "scientist", "manager")):
                jobs.append(
                    JobRecord(
                        title=title,
                        location=None,
                        employment_type=None,
                        department=None,
                        description=title,
                        job_url=href,
                        apply_url=href,
                        source=self.name,
                        source_job_id=None,
                    )
                )
        return jobs
