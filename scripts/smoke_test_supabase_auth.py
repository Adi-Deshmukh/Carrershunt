#!/usr/bin/env python3
"""Interactive Supabase Auth/profile smoke test.

Run from the repository root with:
    python scripts/smoke_test_supabase_auth.py

Credentials are prompted locally and are never written to disk.
"""
from __future__ import annotations

import json
import os
import sys
from getpass import getpass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def request_json(url: str, method: str, headers: dict[str, str], payload: dict | None = None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else None
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(body)
        except json.JSONDecodeError:
            detail = {"message": body[:300]}
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc


def main() -> int:
    env = {**load_env(ROOT / ".env"), **os.environ}
    project_url = env.get("SUPABASE_URL", "").rstrip("/")
    api_key = env.get("SUPABASE_ANON_KEY", "")
    if not project_url or not api_key:
        print("Missing SUPABASE_URL/SUPABASE_ANON_KEY. Run scripts/configure_supabase_env.py first.", file=sys.stderr)
        return 2

    mode = input("Choose [s]ign up or [i]n sign in? ").strip().lower()
    email = input("Email address you control: ").strip()
    password = getpass("Password (input hidden): ")
    if not email or not password:
        print("Email and password are required.", file=sys.stderr)
        return 2

    headers = {"apikey": api_key, "Content-Type": "application/json"}
    try:
        if mode in {"s", "signup", "sign up"}:
            full_name = input("Full name: ").strip()
            _, auth = request_json(
                f"{project_url}/auth/v1/signup",
                "POST",
                headers,
                {"email": email, "password": password, "data": {"full_name": full_name}},
            )
            if not auth or not auth.get("access_token"):
                print("Signup request accepted, but no session was returned. Confirm the email, then rerun in sign-in mode.")
                return 2
        elif mode in {"i", "signin", "sign in", "login"}:
            _, auth = request_json(
                f"{project_url}/auth/v1/token?grant_type=password",
                "POST",
                headers,
                {"email": email, "password": password},
            )
        else:
            print("Choose s or i.", file=sys.stderr)
            return 2

        access_token = auth.get("access_token")
        user_id = (auth.get("user") or {}).get("id")
        if not access_token or not user_id:
            raise RuntimeError("Supabase did not return a valid access token and user ID.")

        authed_headers = {
            **headers,
            "Authorization": f"Bearer {access_token}",
            "Prefer": "return=representation",
        }
        query = urlencode({"id": f"eq.{user_id}", "select": "*"})
        _, rows = request_json(f"{project_url}/rest/v1/profiles?{query}", "GET", authed_headers)
        if not rows:
            raise RuntimeError("No profile row exists for this Auth user; check the signup trigger/migration.")

        profile = rows[0]
        original_name = profile.get("full_name") or ""
        _, updated = request_json(
            f"{project_url}/rest/v1/profiles?id=eq.{user_id}",
            "PATCH",
            authed_headers,
            {"full_name": original_name},
        )
        if not updated:
            raise RuntimeError("Profile update returned no row; verify the RLS update policy.")
        _, verify_rows = request_json(f"{project_url}/rest/v1/profiles?{query}", "GET", authed_headers)
        if not verify_rows or verify_rows[0].get("full_name", "") != original_name:
            raise RuntimeError("Profile read-after-write check failed.")

        print("PASS: Supabase Auth returned a valid session.")
        print("PASS: authenticated user can read their own public.profiles row.")
        print("PASS: profile update and read-after-write succeeded.")
        print(f"User ID: {user_id}")
        print("No password or access token was written to disk.")
        return 0
    except RuntimeError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
