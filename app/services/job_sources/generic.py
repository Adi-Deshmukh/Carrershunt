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


def _same_page(left: str, right: str) -> bool:
    def identity(value: str) -> tuple[str, str]:
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host, parsed.path.rstrip("/") or "/"
    return identity(left) == identity(right)


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
    """Return True only for URL shapes that plausibly identify one job posting.

    Careers-site links containing words like "engineering" or "careers" are
    not enough: culture, benefits, products, and resource pages often live
    under those same paths. Prefer explicit job-detail URL patterns.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False

    path = (parsed.path or "/").lower().rstrip("/") or "/"
    parts = [part for part in path.split("/") if part]
    if not parts:
        return False

    listing_pages = {
        "careers", "career", "jobs", "job", "all-jobs", "openings",
        "positions", "vacancies", "current-openings", "search",
    }
    last = parts[-1]
    if last in listing_pages:
        return False

    platform = _ats_platform(url)
    if platform == "greenhouse":
        # Greenhouse detail URLs use /<board>/jobs/<numeric-id>.
        return len(parts) >= 3 and parts[-2] == "jobs" and parts[-1].isdigit()
    if platform == "lever":
        # Lever detail URLs use /<company>/<posting-slug>.
        return len(parts) >= 2 and last not in listing_pages
    if platform == "ashby":
        # Ashby detail URLs use /<company>/<posting-slug-or-id>.
        return len(parts) >= 2 and last not in listing_pages

    # Explicit job routes, including Atlassian Talent Community's
    # /atlassian-talent-community/jobs/<posting-id>.
    for marker in ("jobs", "job", "positions", "position", "openings",
                   "open-roles", "vacancies", "requisitions"):
        if marker in parts:
            index = parts.index(marker)
            remainder = parts[index + 1:]
            if remainder and remainder[-1] not in listing_pages:
                return True

    # Exclude common informational routes only after checking explicit job
    # routes, so category paths such as /careers/engineering/jobs/123 remain valid.
    excluded_segments = {
        "resources", "resource", "teams", "team", "earlycareers", "early-careers",
        "all-jobs", "alljobs", "employee-awards", "awards", "teamanywhere",
        "team-anywhere", "team-everyone", "benefits", "perk-and-benefits",
        "interviewing", "applying", "career-growth", "products", "product",
        "try", "trust", "marketplace", "developer", "partners", "contact",
        "about", "culture", "values", "locations", "categories",
        "jobs-by-location", "jobs-by-category", "join",
    }
    if any(part in excluded_segments for part in parts):
        return False

    # Some ATS vendors use /careers/<posting-id> or /careers/details/<slug>.
    for marker in ("career", "careers"):
        if marker in parts:
            index = parts.index(marker)
            remainder = parts[index + 1:]
            if len(remainder) >= 2 and remainder[0] in {
                "detail", "details", "job", "jobs", "position", "positions"
            }:
                return True
            if len(remainder) == 1 and (
                remainder[0].isdigit() or re.fullmatch(r"[a-f0-9]{8,}", remainder[0])
            ):
                return True

    return False

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
            for key in ("itemListElement", "mainEntity", "item"):
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

    async def _render_page(self, url: str) -> str | None:
        """Render JavaScript-driven career pages when Playwright + Chromium are installed."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return None
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                try:
                    page = await browser.new_page(user_agent=USER_AGENT)
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception:
                        pass
                    await page.wait_for_timeout(900)
                    return await page.content()
                finally:
                    await browser.close()
        except Exception:
            return None

    async def _rendered_detail(self, url: str, title_hint: str) -> JobRecord | None:
        html = await self._render_page(url)
        if not html:
            return None
        soup = BeautifulSoup(html, "html.parser")
        rendered_url = _canonical_url(soup, url)
        if not _looks_like_job(title_hint, rendered_url):
            return None
        postings = _json_job_postings(soup)
        if postings:
            record = _posting_to_record(postings[0], rendered_url, allow_base_fallback=True)
            if record and len(record.description) >= 100:
                return record
        h1 = soup.select_one("h1")
        title = _clean(h1.get_text(" ", strip=True)) if h1 else title_hint
        description = _page_description(soup)
        if not title or len(description) < 180:
            return None
        apply_url = rendered_url
        for anchor in soup.select("a[href]"):
            label = _clean(anchor.get_text(" ", strip=True)).lower()
            href = _absolute_http_url(anchor.get("href"), rendered_url)
            if href and any(word in label for word in ("apply now", "apply for this job", "submit application")):
                apply_url = href
                break
        return JobRecord(
            title=title[:300],
            location=None,
            employment_type=None,
            department=None,
            description=description,
            job_url=rendered_url,
            apply_url=apply_url,
            source=self.name,
            source_job_id=None,
        )

    async def _fetch_ats_links(self, soup: BeautifulSoup) -> list[JobRecord]:
        candidates: list[tuple[str, str]] = []
        for link in soup.select("a[href], iframe[src], form[action]"):
            raw_href = link.get("href") or link.get("src") or link.get("action")
            href = _absolute_http_url(raw_href, "https://placeholder.invalid/")
            if not href:
                continue
            platform = _ats_platform(href)
            if platform:
                parsed = urlparse(href)
                parts = [part for part in parsed.path.split("/") if part]
                board = parts[0] if parts else (parsed.hostname or "").split(".")[0]
                board_hosts = {
                    "greenhouse": "boards.greenhouse.io",
                    "lever": "jobs.lever.co",
                    "ashby": "jobs.ashbyhq.com",
                }
                board_url = f"https://{board_hosts[platform]}/{board}" if board else href
                candidates.append((platform, board_url))
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
                if record and len(record.description) >= 100 and not _same_page(record.job_url, index_url):
                    jobs[record.job_url] = record

            candidates: list[tuple[str, str]] = []
            for link in soup.select("a[href]"):
                title = _clean(link.get_text(" ", strip=True))
                absolute = _absolute_http_url(link.get("href"), index_url)
                if not absolute or not title or _same_page(absolute, index_url):
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
                        if record and len(record.description) >= 100:
                            return record

                    canonical = _canonical_url(detail_soup, detail_url)
                    # If the link redirected to the index or canonicalized to the
                    # careers homepage, do not persist it as a distinct job.
                    if _same_page(canonical, index_url):
                        return None
                    h1 = detail_soup.select_one("h1")
                    real_title = _clean(h1.get_text(" ", strip=True)) if h1 else title
                    if not _looks_like_job(real_title, canonical):
                        return None
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

            # Browser fallback is deliberately only invoked when static HTML did
            # not yield a usable role. This keeps normal crawls lightweight.
            if not any(len(record.description or "") >= 100 for record in jobs.values()):
                rendered_html = await self._render_page(index_url)
                if rendered_html:
                    rendered_soup = BeautifulSoup(rendered_html, "html.parser")
                    ats_records = await self._fetch_ats_links(rendered_soup)
                    if ats_records:
                        jobs.update({r.job_url: r for r in ats_records if r.job_url and r.title})
                    else:
                        for item in _json_job_postings(rendered_soup):
                            record = _posting_to_record(item, index_url, allow_base_fallback=False)
                            if record and len(record.description) >= 100 and not _same_page(record.job_url, index_url):
                                jobs[record.job_url] = record
                        rendered_candidates = []
                        for link in rendered_soup.select("a[href]"):
                            title = _clean(link.get_text(" ", strip=True))
                            absolute = _absolute_http_url(link.get("href"), index_url)
                            if absolute and title and not _same_page(absolute, index_url) and _looks_like_job(title, absolute):
                                rendered_candidates.append((title, absolute))
                        rendered_unique = []
                        rendered_seen = set()
                        for title, url in rendered_candidates:
                            if url not in rendered_seen:
                                rendered_seen.add(url)
                                rendered_unique.append((title, url))
                        browser_semaphore = asyncio.Semaphore(2)

                        async def render_detail_limited(title: str, url: str) -> JobRecord | None:
                            async with browser_semaphore:
                                return await self._rendered_detail(url, title)

                        rendered_records = await asyncio.gather(*(
                            render_detail_limited(title, url)
                            for title, url in rendered_unique[:8]
                        ))
                        for record in rendered_records:
                            if record and record.job_url:
                                jobs[record.job_url] = record

            return list(jobs.values())
