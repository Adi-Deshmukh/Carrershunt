from app.services.semantic_match import hybrid_match_score, semantic_similarity


def test_semantic_similarity_handles_skill_aliases():
    score = semantic_similarity("Python backend engineer using PostgreSQL and REST APIs", "Built a Python service with Postgres and REST API integrations")
    assert score > 0.20


def test_hybrid_match_prioritizes_required_skills():
    result = hybrid_match_score(["python", "fastapi", "postgresql"], ["kubernetes"], "Python FastAPI PostgreSQL Kubernetes backend service", "Python FastAPI PostgreSQL backend service", {"python", "fastapi", "postgresql"})
    assert result["required_skill_coverage"] == 1.0
    assert result["gaps"] == []
    assert result["score"] >= 70


def test_hybrid_match_reports_required_skill_gaps():
    result = hybrid_match_score(["python", "fastapi"], [], "Python FastAPI backend", "Python backend", {"python"})
    assert result["gaps"] == ["fastapi"]
