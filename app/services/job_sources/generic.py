import asyncio
import json
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.services.job_sources.base import JobRecord, JobSource

JOB_WORDS = (
    "engineer", "developer", "intern", "analyst", "scientist", "manager",
    "designer", "researcher", "product", "security", "data", "machine learning",
    "devops", "architect", "consultant", "associate", "specialist", "qa",
)
JOB_PATH_WORDS = ("/jobs/", "/job/", "/careers/", "/career/", "/positions/", "/position/",
                  "/open-roles/", "/openings/", "/vacancies/", "/requisitions/")
ATS_HOSTS = {
    "greenhouse": ("boards.greenhouse.io", "job-boards.greenhouse.io"),
    "lever": ("jobs.lever.co", "jobs.eu.lever.co"),
    "ashby": ("jobs.ashbyhq.com",),
}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/140 Safari/537.36 Carrershunt/0.3"
)


def _clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _absolute_http_url(url: str | None, base_url: str) -> str | None:
    if not url:
        return None
    absolute = urljoin(base_url, str(url).strip())
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    if parsed.username or parsed.password:
        return None
    return absolute.split("#", 1)[0]


def _ats_platform(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower()
    for platform, hosts in ATS_HOSTS.items():
        if any(host == item or host.endswith("." + item) for item in hosts):
            return platform
    if "greenhouse.io" in host:
        return "greenhouse"
    if host == "lever.co" or host.endswith(".lever.co"):
        return "lever"
    if host == "ashbyhq.com" or host.endswith(".ashbyhq.com"):
        return "ashby"
    return None


def _looks_like_job(title: str, url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    text = f"{title} {path}".lower()
    has_role_word = any(word in text for word in JOB_WORDS)
    has_job_path = any(word in path for word in JOB_PATH_WORDS)
    is_ats = _ats_platform(url) is not None
    last_segment = path.rstrip("/").split("/")[-1] if path.strip("/") else ""
    listing_pages = {"careers", "career", "jobs", "job", "openings", "positions", "vacancies", "current-openings"}
    detail_path = has_job_path and len([part for part in path.split("/") if part]) >= 2 and last_segment not in listing_pages
    return bool(parsed.scheme in {"http", "https"} and (is_ats or (detail_path and (has_role_word or len([part for part in path.split("/") if part]) >= 2))))


def _json_job_postings(soup: BeautifulSoup) -> list[dict]:
    postings: list[dict] = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            payload = json.loads(script.string or script.get_text())
        except (TypeError, ValueError):
            continue
        items = payload if isinstance(payload, list) else [payload]
        while items:
            item = items.pop()
            if not isinstance(item, dict):
                continue
            item_type = item.get("@type", [])
            if isinstance(item_type, str):
                item_type = [item_type]
            if "JobPosting" in item_type:
                postings.append(item)
            graph = item.get("@graph")
            if isinstance(graph, list):
                items.extend(graph)
            for key in ("itemListElement", "mainEntity"):
                nested = item.get(key)
                if isinstance(nested, dict):
                    items.append(nested)
                elif isinstance(nested, list):
                    items.extend(nested)
    return postings


def _posting_to_record(item: dict, base_url: str, allow_base_fallback: bool = False) -> JobRecord | None:
    title = _clean(item.get("title") or item.get("name"))
    raw_url = item.get("url") or item.get("@id")
    url = _absolute_http_url(raw_url, base_url) if raw_url else (
        _absolute_http_url(base_url, base_url) if allow_base_fallback else None
    )
    if not title or not url:
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

    identifier = item.get("identifier")
    if isinstance(identifier, dict):
        identifier = identifier.get("value") or identifier.get("name")
    elif isinstance(identifier, list):
        identifier = ",".join(str(x.get("value", x)) if isinstance(x, dict) else str(x) for x in identifier)

    description = BeautifulSoup(str(item.get("description", "")), "html.parser").get_text(" ", strip=True)
    return JobRecord(
        title=title,
        location=location,
        employment_type=item.get("employmentType") if isinstance(item.get("employmentType"), str) else None,
        department=_clean(item.get("industry")) or None,
        description=_clean(description)[:20000],
        job_url=url,
        apply_url=url,
        source="generic",
        source_job_id=str(identifier) if identifier else None,
    )


def _page_description(soup: BeautifulSoup) -> str:
    for node in soup.select("script, style, nav, footer, header, aside, form, noscript, svg"):
        node.decompose()
    main = soup.select_one("main, article, [role='main'], .job-description, .jobDescription, #job-description")
    text = main.get_text(" ", strip=True) if main else soup.get_text(" ", strip=True)
    return _clean(text)[:20000]


def _canonical_url(soup: BeautifulSoup, fallback_url: str) -> str:
    canonical = soup.select_one('link[rel~="canonical"][href]')
    return _absolute_http_url(canonical.get("href"), fallback_url) if canonical else fallback_url


class GenericSource(JobSource):
    name = "generic"

    async def _fetch_ats_links(self, soup: BeautifulSoup) -> list[JobRecord]:
        candidates: list[tuple[str, str]] = []
        for link in soup.select("a[href]"):
            href = _absolute_http_url(link.get("href"), "https://placeholder.invalid/")
            if not href:
                continue
            platform = _ats_platform(href)
            if platform:
                candidates.append((platform, href))
        # Call the official/public ATS board adapter instead of treating its URL as a
        # generic HTML page. Deduplicate by platform + board URL.
        seen: set[tuple[str, str]] = set()
        results: list[JobRecord] = []
        for platform, url in candidates:
            key = (platform, url)
            if key in seen:
                continue
            seen.add(key)
            if platform == "greenhouse":
                from app.services.job_sources.greenhouse import GreenhouseSource
                source = GreenhouseSource()
            elif platform == "lever":
                from app.services.job_sources.lever import LeverSource
                source = LeverSource()
            else:
                from app.services.job_sources.ashby import AshbySource
                source = AshbySource()
            try:
                records = await source.fetch_jobs(url)
            except (httpx.HTTPError, ValueError, KeyError):
                continue
            results.extend(records)
            if len(results) >= 200:
                break
        return results

    async def fetch_jobs(self, careers_url: str) -> list[JobRecord]:
        normalized_url = _absolute_http_url(careers_url, careers_url)
        if not normalized_url:
            raise ValueError("Careers URL must be an absolute HTTP(S) URL")

        headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8"}
        timeout = httpx.Timeout(25.0, connect=10.0)
        limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
        async with httpx.AsyncClient(timeout=timeout, limits=limits, follow_redirects=True, headers=headers) as client:
            response = await client.get(normalized_url)
            response.raise_for_status()
            index_url = str(response.url)
            soup = BeautifulSoup(response.text, "html.parser")

            # If the company career page links to a supported ATS, use its structured
            # public posting API. This is much more reliable than scraping button text.
            ats_records = await self._fetch_ats_links(soup)
            if ats_records:
                unique = {r.job_url: r for r in ats_records if r.job_url and r.title}
                return list(unique.values())

            jobs: dict[str, JobRecord] = {}
            for item in _json_job_postings(soup):
                record = _posting_to_record(item, index_url, allow_base_fallback=False)
                # Never turn the company careers index itself into a fake job link.
                if record and record.job_url.rstrip("/") != index_url.rstrip("/"):
                    jobs[record.job_url] = record

            candidates: list[tuple[str, str]] = []
            for link in soup.select("a[href]"):
                title = _clean(link.get_text(" ", strip=True))
                absolute = _absolute_http_url(link.get("href"), index_url)
                if not absolute or not title or absolute.rstrip("/") == index_url.rstrip("/"):
                    continue
                if _looks_like_job(title, absolute):
                    candidates.append((title, absolute))

            # Also discover job URLs from a conventional sitemap. Do not crawl every
            # site URL: only paths that look like role pages are eligible.
            sitemap_urls = [urljoin(index_url, "/sitemap.xml")]
            try:
                robots = await client.get(urljoin(index_url, "/robots.txt"))
                if robots.is_success:
                    for line in robots.text.splitlines():
                        if line.lower().startswith("sitemap:"):
                            sitemap_urls.append(line.split(":", 1)[1].strip())
            except httpx.HTTPError:
                pass

            for sitemap_url in dict.fromkeys(sitemap_urls):
                try:
                    sitemap = await client.get(sitemap_url)
                    if not sitemap.is_success or "xml" not in sitemap.headers.get("content-type", "").lower() and "<urlset" not in sitemap.text[:500].lower() and "<sitemapindex" not in sitemap.text[:500].lower():
                        continue
                    sitemap_soup = BeautifulSoup(sitemap.text, "xml")
                    for loc in sitemap_soup.find_all("loc"):
                        target = _absolute_http_url(loc.get_text(strip=True), index_url)
                        if target and _looks_like_job("", target):
                            candidates.append(("", target))
                    if len(candidates) >= 100:
                        break
                except (httpx.HTTPError, ValueError):
                    continue

            unique_candidates: list[tuple[str, str]] = []
            seen_urls: set[str] = set()
            for title, url in candidates:
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_candidates.append((title, url))

            semaphore = asyncio.Semaphore(6)

            async def fetch_detail(title: str, url: str) -> JobRecord | None:
                async with semaphore:
                    try:
                        detail = await client.get(url)
                        detail.raise_for_status()
                    except httpx.HTTPError:
                        return None
                    detail_url = str(detail.url)
                    detail_soup = BeautifulSoup(detail.text, "html.parser")
                    postings = _json_job_postings(detail_soup)
                    if postings:
                        record = _posting_to_record(postings[0], detail_url, allow_base_fallback=True)
                        if record:
                            return record

                    canonical = _canonical_url(detail_soup, detail_url)
                    # If the link redirected to the index or canonicalized to the
                    # careers homepage, do not persist it as a distinct job.
                    if canonical.rstrip("/") == index_url.rstrip("/"):
                        return None
                    h1 = detail_soup.select_one("h1")
                    real_title = _clean(h1.get_text(" ", strip=True)) if h1 else title
                    description = _page_description(detail_soup)
                    if not real_title or len(description) < 180:
                        return None
                    apply_url = canonical
                    for anchor in detail_soup.select("a[href]"):
                        label = _clean(anchor.get_text(" ", strip=True)).lower()
                        href = _absolute_http_url(anchor.get("href"), detail_url)
                        if href and any(word in label for word in ("apply now", "apply for this job", "submit application")):
                            apply_url = href
                            break
                    return JobRecord(
                        title=real_title[:300],
                        location=None,
                        employment_type=None,
                        department=None,
                        description=description,
                        job_url=canonical,
                        apply_url=apply_url,
                        source=self.name,
                        source_job_id=None,
                    )

            detail_results = await asyncio.gather(
                *(fetch_detail(title, url) for title, url in unique_candidates[:60])
            )
            for record in detail_results:
                if record and record.job_url:
                    jobs[record.job_url] = record

            return list(jobs.values())
