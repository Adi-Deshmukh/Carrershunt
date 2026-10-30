from app.services.semantic_match import hybrid_match_score


def test_matches_common_skill_aliases_from_repository_evidence():
    result = hybrid_match_score(
        required_skills=["javascript", "postgresql", "scikit-learn", "rest api"],
        preferred_skills=["github actions"],
        job_text="Build JavaScript REST APIs with PostgreSQL and scikit-learn.",
        candidate_text="Implemented backend services with JS and Postgres.",
        evidence_skills={"JavaScript", "postgres", "sklearn", "restful", "GitHub Actions"},
    )

    assert result["required_skill_coverage"] == 1.0
    assert result["preferred_skill_coverage"] == 1.0
    assert result["gaps"] == []


def test_reports_unmatched_required_skill():
    result = hybrid_match_score(
        required_skills=["Python", "Kubernetes"],
        preferred_skills=[],
        job_text="Python Kubernetes",
        candidate_text="Python scripts",
        evidence_skills={"Python"},
    )

    assert result["matched_required_skills"] == ["Python"]
    assert result["gaps"] == ["Kubernetes"]
