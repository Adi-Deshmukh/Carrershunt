"""Browser-backed adapters for career sites whose listings are rendered client-side.

These sites are public to browse, but their job cards are often absent from the
initial HTML returned to a simple HTTP client. We use the installed Playwright
runtime to discover real detail links, then validate each detail page before
returning it to ingestion.
"""
from __future__ import annotations

import asyncio
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.services.job_sources.base import JobRecord, JobSource
from app.services.job_sources.generic import (
    GenericSource,
    _absolute_http_url,
    _canonical_url,
    _clean,
    _page_description,
)

MAX_DETAIL_PAGES = 50


def _site(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower()
    if host == "atlassian.com" or host.endswith(".atlassian.com") or host.endswith(".atlassian.net"):
        return "atlassian"
    if host == "google.com" or host.endswith(".google.com"):
        return "google"
    if host == "careers.microsoft.com" or host.endswith(".microsoft.com"):
        return "microsoft"
    return None


def _detail_candidate(site: str, url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    if parsed.scheme not in {"http", "https"}:
        return False
    if site == "google":
        return host.endswith("google.com") and bool(
            re.search(r"/about/careers/applications/jobs/results/\d{6,}", path)
        )
    if site == "atlassian":
        return (
            host.endswith("atlassian.com")
            and "/company/careers/" in path
            and any(token in path for token in ("/details/", "/job/", "/jobs/"))
            and not any(token in path for token in ("/all-jobs", "/resources/", "/engineering"))
        ) or (host == "join.atlassian.com" and "/jobs/" in path)
    if site == "microsoft":
        return host.endswith("microsoft.com") and bool(
            re.search(r"/(?:job|jobs|jobdetails|job-detail|jobdetail)/", path)
            or re.search(r"/job/[^/]+", path)
        )
    return False


class CompanyCareersSource(JobSource):
    name = "company_careers"

    async def fetch_jobs(self, careers_url: str) -> list[JobRecord]:
        site = _site(careers_url)
        if not site:
            raise ValueError("CompanyCareersSource only supports Atlassian, Google, and Microsoft")

        generic = GenericSource()
        # Try existing static/API extraction first. Some pages do expose structured data.
        try:
            records = await generic.fetch_jobs(careers_url)
        except Exception:
            records = []
        if records:
            for record in records:
                record.source = site
            return records

        html = await generic._render_page(careers_url)
        if not html:
            raise RuntimeError(
                "Could not render this careers page. Install Playwright Chromium "
                "(python -m playwright install chromium) and verify outbound access from the worker."
            )

        soup = BeautifulSoup(html, "html.parser")
        base_url = careers_url
        canonical = _canonical_url(soup, base_url)
        candidates: dict[str, str] = {}

        # Collect real detail URLs from the rendered DOM. Prefer anchors that look
        # like job cards, but also inspect all anchors because some sites use icon-only links.
        for anchor in soup.select("a[href]"):
            href = _absolute_http_url(anchor.get("href"), base_url)
            if not href or not _detail_candidate(site, href):
                continue
            title = _clean(anchor.get_text(" ", strip=True))
            if not title:
                title = _clean(anchor.get("aria-label") or anchor.get("title") or "")
            if title and len(title) <= 300:
                candidates[href] = title

        # Google can expose a search-results page URL with the job ID in the URL.
        # If the user provided a Google detail page directly, include it as a candidate.
        if _detail_candidate(site, careers_url):
            candidates[careers_url] = ""

        if not candidates:
            raise RuntimeError(
                f"{site.title()} page rendered, but no supported job-detail links were found. "
                "The site may have changed its URL structure or returned a bot-check page."
            )

        semaphore = asyncio.Semaphore(4)

        async def parse_detail(url: str, title_hint: str) -> JobRecord | None:
            async with semaphore:
                # Use a fresh rendered browser context for detail pages because the
                # content is often hydrated by JavaScript after initial navigation.
                detail_html = await generic._render_page(url)
                if not detail_html:
                    return None
                detail_soup = BeautifulSoup(detail_html, "html.parser")
                detail_url = _canonical_url(detail_soup, url)
                if not _detail_candidate(site, detail_url):
                    return None

                # JSON-LD is the most reliable source when the publisher provides it.
                from app.services.job_sources.generic import _json_job_postings, _posting_to_record
                postings = _json_job_postings(detail_soup)
                if postings:
                    record = _posting_to_record(postings[0], detail_url, allow_base_fallback=True)
                    if record and len(record.description) >= 100:
                        record.source = site
                        return record

                h1 = detail_soup.select_one("h1")
                title = _clean(h1.get_text(" ", strip=True)) if h1 else title_hint
                description = _page_description(detail_soup)
                # Avoid storing search/index pages and bot-check pages as jobs.
                if not title or len(description) < 180:
                    return None
                lowered = title.lower()
                if any(phrase in lowered for phrase in (
                    "search jobs", "jobs search", "careers home", "browse jobs",
                    "job not found", "access denied", "verify you are human",
                )):
                    return None

                location = None
                body_text = detail_soup.get_text(" ", strip=True)
                location_match = re.search(
                    r"(?:Location|Locations)\s*[:\-]?\s*([^|]{2,100}?)(?:\s{2,}|Overview|Responsibilities|Qualifications)",
                    body_text,
                    re.IGNORECASE,
                )
                if location_match:
                    location = _clean(location_match.group(1))[:200]

                apply_url = detail_url
                for anchor in detail_soup.select("a[href]"):
                    label = _clean(anchor.get_text(" ", strip=True)).lower()
                    href = _absolute_http_url(anchor.get("href"), detail_url)
                    if href and any(word in label for word in ("apply now", "apply", "submit application")):
                        apply_url = href
                        break

                return JobRecord(
                    title=title[:300],
                    location=location,
                    employment_type=None,
                    department=None,
                    description=description[:20000],
                    job_url=detail_url,
                    apply_url=apply_url,
                    source=site,
                    source_job_id=None,
                )

        results = await asyncio.gather(*(
            parse_detail(url, title)
            for url, title in list(candidates.items())[:MAX_DETAIL_PAGES]
        ))
        unique = {record.job_url: record for record in results if record and record.job_url}
        if not unique:
            raise RuntimeError(
                f"Found {len(candidates)} candidate links on {site.title()}, but none passed "
                "job-detail validation (title/description/URL). Check worker browser logs and site markup."
            )
        return list(unique.values())
