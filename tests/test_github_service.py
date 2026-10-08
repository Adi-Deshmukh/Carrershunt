from app.services.github_service import normalize_github_username


def test_normalize_github_username() -> None:
    assert normalize_github_username("Adi-Deshmukh") == "Adi-Deshmukh"
    assert normalize_github_username("@Adi-Deshmukh") == "Adi-Deshmukh"
    assert normalize_github_username("https://github.com/Adi-Deshmukh") == "Adi-Deshmukh"


def test_reject_invalid_github_username() -> None:
    import pytest
    with pytest.raises(ValueError):
        normalize_github_username("https://github.com/")
