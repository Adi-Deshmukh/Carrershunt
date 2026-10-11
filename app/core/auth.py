"""Supabase Auth token verification for FastAPI routes.

The API validates bearer tokens against Supabase Auth's /user endpoint instead
of decoding unverified JWT claims. Without Supabase credentials, local development
runs in single-user mode with an anonymous development identity.
"""
from __future__ import annotations

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


def supabase_enabled() -> bool:
    return bool(settings.supabase_url.strip() and settings.supabase_anon_key.strip())


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if not supabase_enabled():
        return {"id": None, "email": None, "authenticated": False}

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Sign in to continue.")

    url = settings.supabase_url.rstrip("/") + "/auth/v1/user"
    try:
        response = httpx.get(
            url,
            headers={
                "apikey": settings.supabase_anon_key,
                "Authorization": f"Bearer {credentials.credentials}",
            },
            timeout=5.0,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Supabase Auth is temporarily unavailable.") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Your session is invalid or expired. Sign in again.")

    user = response.json()
    if not user.get("id"):
        raise HTTPException(status_code=401, detail="Supabase did not return a valid user.")
    return {
        "id": str(user["id"]),
        "email": user.get("email"),
        "authenticated": True,
        "metadata": user.get("user_metadata") or {},
    }


def require_user_id(user: dict) -> str | None:
    return user.get("id")
