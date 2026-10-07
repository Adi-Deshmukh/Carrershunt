from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from urllib.parse import urlsplit, urlunsplit

import pandas as pd
from pydantic import HttpUrl, TypeAdapter, ValidationError

from app.schemas.company import CompanyCreate

_URL_ADAPTER = TypeAdapter(HttpUrl)
REQUIRED_COLUMNS = {"company", "careers_url"}


@dataclass
class ImportResult:
    imported: list[CompanyCreate]
    duplicates: list[str]
    invalid: list[dict[str, str]]


def normalize_url(value: object) -> str:
    url = str(value).strip()
    parsed = urlsplit(url if "://" in url else f"https://{url}")

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Invalid HTTP(S) URL")

    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        fragment="",
    )
    path = normalized.path.rstrip("/") or "/"
    return urlunsplit(
        (normalized.scheme, normalized.netloc, path, normalized.query, "")
    )


def normalize_company_name(value: object) -> str:
    return " ".join(str(value).strip().split())


def import_companies(file_bytes: bytes) -> ImportResult:
    df = pd.read_excel(BytesIO(file_bytes))

    normalized_columns = {
        str(column).strip().lower(): column for column in df.columns
    }
    missing = REQUIRED_COLUMNS - set(normalized_columns)
    if missing:
        raise ValueError(
            "Missing required columns: " + ", ".join(sorted(missing))
        )

    imported: list[CompanyCreate] = []
    duplicates: list[str] = []
    invalid: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for row_number, row in enumerate(df.to_dict(orient="records"), start=2):
        raw_name = row[normalized_columns["company"]]
        raw_url = row[normalized_columns["careers_url"]]

        if pd.isna(raw_name) or pd.isna(raw_url):
            invalid.append(
                {"row": str(row_number), "reason": "company and careers_url are required"}
            )
            continue

        try:
            name = normalize_company_name(raw_name)
            url = normalize_url(raw_url)
            validated_url = str(_URL_ADAPTER.validate_python(url))
            company = CompanyCreate(name=name, careers_url=validated_url)
        except (ValueError, ValidationError) as exc:
            invalid.append({"row": str(row_number), "reason": str(exc)})
            continue

        key = (company.name.casefold(), str(company.careers_url).casefold())
        if key in seen:
            duplicates.append(company.name)
            continue

        seen.add(key)
        imported.append(company)

    return ImportResult(
        imported=imported,
        duplicates=duplicates,
        invalid=invalid,
    )
