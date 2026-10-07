from urllib.parse import urlparse

import httpx

from app.services.job_sources.base import JobRecord, JobSource


class GreenhouseSource(JobSource):
    name = "greenhouse"

    async def fetch_jobs(self, careers_url: str) -> list[JobRecord]:
        parsed = urlparse(careers_url)
        board_token = parsed.path.strip("/").split("/")[0]
        if not board_token:
            return []

        url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()

        jobs = []
        for item in payload.get("jobs", []):
            jobs.append(
                JobRecord(
                    title=item["title"],
                    location=(item.get("location") or {}).get("name"),
                    employment_type=None,
                    department=None,
                    description=item.get("content", ""),
                    job_url=item.get("absolute_url", ""),
                    apply_url=item.get("absolute_url"),
                    source=self.name,
                    source_job_id=str(item.get("id")) if item.get("id") else None,
                )
            )
        return jobs
