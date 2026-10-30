from app.services.github_service import normalize_github_username


def test_normalize_github_username() -> None:
    assert normalize_github_username("Adi-Deshmukh") == "Adi-Deshmukh"
    assert normalize_github_username("@Adi-Deshmukh") == "Adi-Deshmukh"
    assert normalize_github_username("https://github.com/Adi-Deshmukh") == "Adi-Deshmukh"


def test_reject_invalid_github_username() -> None:
    import pytest
    with pytest.raises(ValueError):
        normalize_github_username("https://github.com/")


def test_repo_skills_include_frameworks_and_data_stack_from_readme():
    from app.services.github_service import _repo_skills

    skills = _repo_skills(
        {"Python": 1000, "TypeScript": 300},
        ["machine-learning", "postgres"],
        "Built a FastAPI service with React, Docker, PostgreSQL, scikit-learn and GitHub Actions.",
    )

    assert {"Python", "TypeScript", "fastapi", "react", "docker", "postgresql", "scikit-learn", "github actions"} <= set(skills)


def test_repo_summary_preserves_project_metadata():
    from app.services.github_service import _repo_summary

    summary = _repo_summary(
        {"full_name": "owner/project", "description": "Analytics platform", "language": "Python"},
        {"Python": 100, "SQL": 50},
        ["data-science"],
        "# Project\\nUses pandas and XGBoost.",
    )

    assert "owner/project" in summary
    assert "Analytics platform" in summary
    assert "XGBoost" in summary
