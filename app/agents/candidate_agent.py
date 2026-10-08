from app.services.agent_service import AgentService


class CandidateIntelligenceAgent:
    name = "candidate_intelligence"

    def __init__(self, service: AgentService | None = None):
        self.service = service or AgentService()

    def run(self, state: dict) -> dict:
        job = state["job"]
        candidate = state["candidate_record"]
        query = " ".join(job.required_skills + job.preferred_skills + job.responsibilities[:5])
        state["evidence"] = self.service.build_candidate_context(state["db"], candidate, query)
        return state
