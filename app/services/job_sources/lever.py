from urllib.parse import urlparse

import httpx

from app.services.job_sources.base import JobRecord, JobSource


class LeverSource(JobSource):
    name = "lever"

    async def fetch_jobs(self, careers_url: str) -> list[JobRecord]:
        parsed = urlparse(careers_url)
        parts = [p for p in parsed.path.split("/") if p]
        site = parts[0] if parts else parsed.hostname.split(".")[0]
        url = f"https://api.lever.co/v0/postings/{site}?mode=json"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()

        jobs = []
        for item in payload:
            categories = item.get("categories", {})
            description = item.get("descriptionPlain") or item.get("description") or ""
            jobs.append(
                JobRecord(
                    title=item.get("text", ""),
                    location=categories.get("location"),
                    employment_type=categories.get("commitment"),
                    department=categories.get("department"),
                    description=description,
                    job_url=item.get("hostedUrl", ""),
                    apply_url=item.get("applyUrl"),
                    source=self.name,
                    source_job_id=item.get("id"),
                )
            )
        return jobs
