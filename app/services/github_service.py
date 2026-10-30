import base64
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.services.evidence import EvidenceInput, upsert_evidence

GITHUB_API = "https://api.github.com"
REPO_SKILL_ALIASES = {
    "postgres": "postgresql",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "sklearn": "scikit-learn",
    "pytorch": "pytorch",
    "tf": "tensorflow",
    "k8s": "kubernetes",
}
PROJECT_SKILLS = (
    "python", "java", "javascript", "typescript", "react", "next.js", "node.js",
    "django", "fastapi", "flask", "express", "postgresql", "mysql", "mongodb",
    "redis", "sqlite", "firebase", "supabase", "docker", "kubernetes", "aws",
    "azure", "gcp", "terraform", "github actions", "ci/cd", "machine learning",
    "deep learning", "nlp", "computer vision", "pytorch", "tensorflow",
    "scikit-learn", "xgboost", "pandas", "numpy", "langchain", "llm", "rag",
    "vector database", "chromadb", "faiss", "spark", "hadoop", "airflow",
    "kafka", "graphql", "rest api", "websocket", "unity", "c#", "c++", "rust",
    "go", "linux", "html", "css", "sql", "git",
)


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
        "User-Agent": "Carrershunt/0.2",
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


def _repo_skills(languages: dict[str, Any], topics: list[str], text: str) -> list[str]:
    searchable = " ".join([*languages.keys(), *topics, text]).lower()
    found = set()
    for skill in PROJECT_SKILLS:
        if re.search(rf"(?<![a-z0-9]){re.escape(skill.lower())}(?![a-z0-9])", searchable):
            found.add(skill)
    for alias, canonical in REPO_SKILL_ALIASES.items():
        if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", searchable):
            found.add(canonical)
    found.update(languages.keys())
    return sorted(found)


def _repo_summary(repo: dict[str, Any], languages: dict[str, Any], topics: list[str], readme: str) -> str:
    sections = [
        f"Repository: {repo.get('full_name', repo.get('name', ''))}",
        f"Description: {repo.get('description') or 'Not provided'}",
        f"Primary language: {repo.get('language') or 'Not provided'}",
        "Languages: " + ", ".join(languages.keys()),
        "Topics: " + ", ".join(topics),
    ]
    if readme:
        sections.append("README evidence:\n" + readme[:12000])
    return "\n".join(sections)


async def sync_github(db, candidate_id: int, username_or_url: str, max_repos: int = 25) -> GitHubSyncResult:
    username = normalize_github_username(username_or_url)
    if max_repos < 1 or max_repos > 100:
        raise ValueError("max_repos must be between 1 and 100")

    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
        profile_response = await _get(client, f"/users/{username}")
        profile = profile_response.json()
        repos_response = await _get(
            client,
            f"/users/{username}/repos?per_page={max_repos}&sort=updated&direction=desc&type=owner",
        )
        repos = repos_response.json()

        upserted = 0
        profile_text = " ".join(filter(None, [
            profile.get("name"), profile.get("bio"), profile.get("company"), profile.get("location")
        ]))
        if profile_text:
            upsert_evidence(db, candidate_id, EvidenceInput(
                source="github", source_key=f"user:{username}",
                title=f"GitHub profile: {profile.get('name') or username}",
                content=profile_text, url=profile.get("html_url"),
                evidence_type="profile", skills=[],
                metadata={"username": username, "public_repos": profile.get("public_repos", 0)},
            ))
            upserted += 1

        repos_seen = 0
        for repo in repos:
            if repo.get("fork") or repo.get("archived"):
                continue
            repos_seen += 1
            owner = (repo.get("owner") or {}).get("login") or username
            repo_name = repo["name"]
            prefix = f"/repos/{owner}/{repo_name}"

            # Individual ancillary endpoints must not discard the rest of a
            # repository when a README/language endpoint is unavailable.
            readme_text = ""
            try:
                readme = (await _get(client, f"{prefix}/readme")).json()
                encoded = (readme.get("content") or "").replace("\\n", "")
                readme_text = base64.b64decode(encoded).decode("utf-8", errors="replace")
            except (ValueError, httpx.HTTPError, KeyError, TypeError):
                pass

            try:
                languages: dict[str, Any] = (await _get(client, f"{prefix}/languages")).json()
            except (ValueError, httpx.HTTPError):
                languages = {}

            topics = repo.get("topics") or []
            summary = _repo_summary(repo, languages, topics, readme_text)
            skills = _repo_skills(languages, topics, summary)
            upsert_evidence(db, candidate_id, EvidenceInput(
                source="github",
                source_key=f"repo:{repo.get('full_name') or owner + '/' + repo_name}",
                title=repo_name,
                content=summary,
                url=repo.get("html_url"),
                evidence_type="project",
                skills=skills,
                metadata={
                    "repository": repo.get("full_name") or f"{owner}/{repo_name}",
                    "description": repo.get("description"),
                    "language": repo.get("language"),
                    "languages": languages,
                    "topics": topics,
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "default_branch": repo.get("default_branch"),
                    "updated_at": repo.get("updated_at"),
                    "readme_indexed": bool(readme_text),
                },
            ))
            upserted += 1

        db.commit()
        remaining = repos_response.headers.get("X-RateLimit-Remaining")
        return GitHubSyncResult(
            username=username,
            repositories_seen=repos_seen,
            repositories_indexed=repos_seen,
            evidence_created_or_updated=upserted,
            rate_limit_remaining=int(remaining) if remaining and remaining.isdigit() else None,
        )
