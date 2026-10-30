from types import SimpleNamespace

from app.services.agent_service import AgentService


class FakeDB:
    pass


def test_candidate_context_includes_indexed_project_evidence(monkeypatch):
    focused = [{"id": 1, "type": "profile", "title": "Profile", "content": "Data engineer"}]
    projects = [{"id": 2, "type": "project", "title": "Portfolio API", "content": "Built FastAPI service"}]

    def fake_retrieve(db, candidate_id, query, limit=8, evidence_type=None):
        if evidence_type == "project":
            return projects
        return focused

    monkeypatch.setattr("app.services.agent_service.retrieve_evidence", fake_retrieve)
    result = AgentService().build_candidate_context(FakeDB(), SimpleNamespace(id=7), "Python")

    assert [item["id"] for item in result] == [1, 2]


def test_resume_plan_uses_evidence_skills(monkeypatch):
    service = AgentService()
    candidate = SimpleNamespace(name="Candidate", experience_years=0, resume_text="B.Tech graduate")
    structured = SimpleNamespace(title="Backend Developer", required_skills=["FastAPI"], preferred_skills=[])
    match = SimpleNamespace()
    evidence = [{
        "id": 2,
        "type": "project",
        "title": "Portfolio API",
        "content": "Built a FastAPI service with REST endpoints.",
        "skills": ["fastapi"],
        "source": "github",
    }]
    monkeypatch.setattr("app.services.agent_service.validate_resume_plan", lambda plan, ev, text: [])

    plan, errors = service.resume_plan(candidate, structured, match, evidence)

    assert errors == []
    assert "FastAPI" in plan.skills
    assert plan.projects[0].name == "Portfolio API"
