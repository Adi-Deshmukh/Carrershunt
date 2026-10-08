import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.services.evidence import EvidenceInput, upsert_evidence


GITHUB_API = "https://api.github.com"


@dataclass
class GitHubSyncResult:
    username: str
    repositories_seen: int
    repositories_indexed: int
    evidence_created_or_updated: int
    rate_limit_remaining: int | None


def normalize_github_username(value: str) -> str:
    value = value.strip()
    if value.startswith("http"):
        parsed = urlparse(value)
        parts = [p for p in parsed.path.split("/") if p]
        if not parts:
            raise ValueError("GitHub URL does not contain a username")
        value = parts[0]
    value = value.lstrip("@").strip("/")
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", value):
        raise ValueError("Invalid GitHub username")
    return value


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Carrershunt/0.1",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


async def _get(client: httpx.AsyncClient, path: str) -> httpx.Response:
    response = await client.get(f"{GITHUB_API}{path}", headers=_headers())
    if response.status_code == 404:
        raise ValueError(f"GitHub resource not found: {path}")
    if response.status_code == 403:
        remaining = response.headers.get("X-RateLimit-Remaining")
        raise RuntimeError(
            f"GitHub API rate limit or access restriction. Remaining: {remaining or 'unknown'}"
        )
    response.raise_for_status()
    return response


async def sync_github(db, candidate_id: int, username_or_url: str, max_repos: int = 25) -> GitHubSyncResult:
    username = normalize_github_username(username_or_url)
    if max_repos < 1 or max_repos > 100:
        raise ValueError("max_repos must be between 1 and 100")

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        profile_response = await _get(client, f"/users/{username}")
        profile = profile_response.json()

        repos_response = await _get(
            client,
            f"/users/{username}/repos?per_page={max_repos}&sort=updated&direction=desc&type=owner",
        )
        repos = repos_response.json()

        count = 0
        upserted = 0

        profile_text = " ".join(
            filter(None, [
                profile.get("name"),
                profile.get("bio"),
                profile.get("company"),
                profile.get("location"),
            ])
        )
        if profile_text:
            upsert_evidence(
                db,
                candidate_id,
                EvidenceInput(
                    source="github",
                    source_key=f"user:{username}",
                    title=f"GitHub profile: {profile.get('name') or username}",
                    content=profile_text,
                    url=profile.get("html_url"),
                    evidence_type="profile",
                    skills=[],
                    metadata={"username": username, "public_repos": profile.get("public_repos", 0)},
                ),
            )
            upserted += 1

        for repo in repos:
            if repo.get("fork"):
                continue
            count += 1

            readme_text = ""
            try:
                readme_response = await _get(
                    client, f"/repos/{username}/{repo['name']}/readme"
                )
                readme = readme_response.json()
                import base64
                readme_text = base64.b64decode(
                    (readme.get("content") or "").replace("\n", "")
                ).decode("utf-8", errors="replace")
            except (ValueError, httpx.HTTPError):
                readme_text = ""

            languages_response = await _get(
                client, f"/repos/{username}/{repo['name']}/languages"
            )
            languages: dict[str, Any] = languages_response.json()

            topics = repo.get("topics") or []
            skills = sorted(set([*languages.keys(), *topics]))
            sections = [
                repo.get("name", ""),
                repo.get("description") or "",
                "Topics: " + ", ".join(topics),
                "Languages: " + ", ".join(languages.keys()),
            ]
            if readme_text:
                sections.append("README:\n" + readme_text[:12000])

            content = "\n".join(s for s in sections if s).strip()
            if not content:
                continue

            upsert_evidence(
                db,
                candidate_id,
                EvidenceInput(
                    source="github",
                    source_key=f"repo:{repo['full_name']}",
                    title=repo["name"],
                    content=content,
                    url=repo.get("html_url"),
                    evidence_type="project",
                    skills=skills,
                    metadata={
                        "repository": repo["full_name"],
                        "stars": repo.get("stargazers_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "default_branch": repo.get("default_branch"),
                        "updated_at": repo.get("updated_at"),
                    },
                ),
            )
            upserted += 1

        db.commit()

        remaining = repos_response.headers.get("X-RateLimit-Remaining")
        return GitHubSyncResult(
            username=username,
            repositories_seen=count,
            repositories_indexed=count,
            evidence_created_or_updated=upserted,
            rate_limit_remaining=int(remaining) if remaining and remaining.isdigit() else None,
        )
