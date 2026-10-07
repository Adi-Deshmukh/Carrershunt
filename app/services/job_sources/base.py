from dataclasses import dataclass


@dataclass
class JobRecord:
    title: str
    location: str | None
    employment_type: str | None
    department: str | None
    description: str
    job_url: str
    apply_url: str | None
    source: str
    source_job_id: str | None


class JobSource:
    name = "base"

    async def fetch_jobs(self, careers_url: str) -> list[JobRecord]:
        raise NotImplementedError
