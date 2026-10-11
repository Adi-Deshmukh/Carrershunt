#!/usr/bin/env python3
"""Populate local Supabase environment variables without overwriting other settings.

Run from any directory:
    python scripts/configure_supabase_env.py

The Supabase publishable key is intended for browser use. Never use a service-role
or secret key in VITE_* variables. Generated .env files are gitignored.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT_URL = "https://tqvmfghgficvncyjjxiz.supabase.co"
PUBLISHABLE_KEY = "sb_publishable_mCFj56qTIs__pYJ1l1l-TA_7llIpxrV"


def update_env(path: Path, template_path: Path, values: dict[str, str]) -> None:
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    elif template_path.exists():
        lines = template_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    for key, value in values.items():
        pattern = re.compile(rf"^\\s*{re.escape(key)}\\s*=.*$")
        matching = [i for i, line in enumerate(lines) if pattern.match(line)]
        replacement = f"{key}={value}"
        if matching:
            lines[matching[0]] = replacement
            for duplicate_index in reversed(matching[1:]):
                del lines[duplicate_index]
        else:
            if lines and lines[-1].strip():
                lines.append("")
            lines.append(replacement)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\\n".join(lines).rstrip() + "\\n", encoding="utf-8")


def main() -> None:
    update_env(
        ROOT / ".env",
        ROOT / ".env.example",
        {"SUPABASE_URL": PROJECT_URL, "SUPABASE_ANON_KEY": PUBLISHABLE_KEY},
    )
    update_env(
        ROOT / "frontend" / ".env",
        ROOT / "frontend" / ".env.example",
        {"VITE_SUPABASE_URL": PROJECT_URL, "VITE_SUPABASE_ANON_KEY": PUBLISHABLE_KEY},
    )
    print("Configured .env and frontend/.env for the Carrershunt Supabase project.")
    print("Existing non-Supabase environment variables were preserved.")
    print("Restart FastAPI and Vite, then test sign-up/sign-in and profile persistence.")


if __name__ == "__main__":
    main()
