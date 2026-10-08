import json
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


def _json_job_postings(soup: BeautifulSoup) -> list[dict]:
    postings = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            payload = json.loads(script.string or script.get_text())
        except (TypeError, ValueError):
            continue
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("@type") == "JobPosting":
                postings.append(item)
            graph = item.get("@graph")
            if isinstance(graph, list):
                postings.extend(x for x in graph if isinstance(x, dict) and x.get("@type") == "JobPosting")
    return postings


def _posting_to_record(item: dict, fallback_url: str) -> JobRecord | None:
    title = _clean(item.get("title"))
    url = item.get("url") or fallback_url
    if not title:
        return None

    location = None
    locations = item.get("jobLocation")
    if isinstance(locations, dict):
        locations = [locations]
    if isinstance(locations, list):
        values = []
        for loc in locations:
            address = loc.get("address", {}) if isinstance(loc, dict) else {}
            if isinstance(address, dict):
                parts = [
                    _clean(address.get("addressLocality")),
                    _clean(address.get("addressRegion")),
                    _clean(address.get("addressCountry")),
                ]
                values.append(", ".join(x for x in parts if x))
        location = "; ".join(x for x in values if x) or None

    return JobRecord(
        title=title,
        location=location,
        employment_type=item.get("employmentType"),
        department=None,
        description=_clean(BeautifulSoup(str(item.get("description", "")), "html.parser").get_text(" ")),
        job_url=url,
        apply_url=url,
        source="generic",
        source_job_id=str(item.get("identifier", {}).get("value")) if isinstance(item.get("identifier"), dict) else None,
    )


class GenericSource(JobSource):
    name = "generic"

    async def fetch_jobs(self, careers_url: str) -> list[JobRecord]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/140 Safari/537.36 Carrershunt/0.2"
            )
        }
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=headers) as client:
            response = await client.get(careers_url)
            response.raise_for_status()
            page_html = response.text

            soup = BeautifulSoup(page_html, "html.parser")
            jobs: dict[str, JobRecord] = {}

            # First choice: structured JobPosting data on the careers index.
            for item in _json_job_postings(soup):
                record = _posting_to_record(item, careers_url)
                if record:
                    jobs[record.job_url] = record

            # Second choice: job-like links. Fetch each detail page so the
            # pipeline receives an actual JD rather than only the link text.
            candidates = []
            for link in soup.select("a[href]"):
                title = _clean(link.get_text(" ", strip=True))
                href = link.get("href")
                if not href or not title:
                    continue
                absolute = urljoin(careers_url, href)
                if _looks_like_job(title, absolute):
                    candidates.append((title, absolute))

            seen_urls = set()
            for title, absolute in candidates[:40]:
                if absolute in seen_urls or absolute in jobs:
                    continue
                seen_urls.add(absolute)
                record = None
                try:
                    detail = await client.get(absolute)
                    detail.raise_for_status()
                    detail_soup = BeautifulSoup(detail.text, "html.parser")
                    postings = _json_job_postings(detail_soup)
                    if postings:
                        record = _posting_to_record(postings[0], absolute)
                    if record is None:
                        description = _clean(
                            detail_soup.get_text(" ", strip=True)
                        )
                        # Keep a bounded but useful description for deterministic
                        # parsing when the page has no structured JobPosting data.
                        record = JobRecord(
                            title=title,
                            location=None,
                            employment_type=None,
                            department=None,
                            description=description[:20000],
                            job_url=absolute,
                            apply_url=absolute,
                            source=self.name,
                            source_job_id=None,
                        )
                except httpx.HTTPError:
                    # The index result is still useful even when a detail page blocks.
                    record = JobRecord(
                        title=title,
                        location=None,
                        employment_type=None,
                        department=None,
                        description=title,
                        job_url=absolute,
                        apply_url=absolute,
                        source=self.name,
                        source_job_id=None,
                    )

                if record:
                    jobs[record.job_url] = record

            return list(jobs.values())
