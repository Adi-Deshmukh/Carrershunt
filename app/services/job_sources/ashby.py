from urllib.parse import urlparse

import httpx

from app.services.job_sources.base import JobRecord, JobSource


class AshbySource(JobSource):
    name = "ashby"

    async def fetch_jobs(self, careers_url: str) -> list[JobRecord]:
        parsed = urlparse(careers_url)
        parts = [p for p in parsed.path.split("/") if p]
        board = parts[0] if parts else ""
        if not board:
            return []

        url = f"https://api.ashbyhq.com/posting-api/job-board/{board}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()

        jobs = []
        for item in payload.get("jobs", []):
            jobs.append(
                JobRecord(
                    title=item.get("title", ""),
                    location=item.get("location"),
                    employment_type=item.get("employmentType"),
                    department=item.get("department"),
                    description=item.get("descriptionPlain") or item.get("descriptionHtml", ""),
                    job_url=item.get("jobUrl", ""),
                    apply_url=item.get("applyUrl"),
                    source=self.name,
                    source_job_id=item.get("jobUrl"),
                )
            )
        return jobs
