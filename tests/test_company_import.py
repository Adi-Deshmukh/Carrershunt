from io import BytesIO

import pandas as pd
import pytest

from app.services.company_import import import_companies, normalize_url


def make_excel(rows: list[dict]) -> bytes:
    buffer = BytesIO()
    pd.DataFrame(rows).to_excel(buffer, index=False)
    return buffer.getvalue()


def test_imports_valid_companies_and_removes_duplicate_rows() -> None:
    content = make_excel(
        [
            {"company": " NVIDIA ", "careers_url": "https://careers.nvidia.com/"},
            {"company": "NVIDIA", "careers_url": "https://careers.nvidia.com"},
            {"company": "Stripe", "careers_url": "stripe.com/jobs/"},
        ]
    )

    result = import_companies(content)

    assert len(result.imported) == 2
    assert result.duplicates == ["NVIDIA"]
    assert result.imported[0].name == "NVIDIA"


def test_import_accepts_common_human_friendly_column_aliases() -> None:
    content = make_excel(
        [
            {"name": "NVIDIA", "url": "https://example.com/jobs"},
            {"Company Name": "Stripe", "Jobs URL": "https://stripe.com/jobs"},
        ]
    )

    result = import_companies(content)

    assert [company.name for company in result.imported] == ["NVIDIA", "Stripe"]


def test_import_reports_invalid_rows() -> None:
    content = make_excel(
        [
            {"company": "GoodCo", "careers_url": "https://example.com/jobs"},
            {"company": "BadCo", "careers_url": "not a url"},
            {"company": "", "careers_url": "https://example.com"},
        ]
    )

    result = import_companies(content)

    assert len(result.imported) == 1
    assert len(result.invalid) == 2


def test_missing_required_columns_are_rejected() -> None:
    content = make_excel([{"ticker": "NVIDIA", "website": "https://example.com"}])

    with pytest.raises(ValueError, match="Missing required columns"):
        import_companies(content)


def test_normalize_url_adds_scheme_and_removes_fragment() -> None:
    assert normalize_url("example.com/jobs/#openings") == "https://example.com/jobs"
