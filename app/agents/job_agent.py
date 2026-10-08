from app.services.agent_service import AgentService


class JobIntelligenceAgent:
    name = "job_intelligence"

    def __init__(self, service: AgentService | None = None):
        self.service = service or AgentService()

    def run(self, state: dict) -> dict:
        state["job"] = self.service.structure_job(state["job_record"], use_llm=state.get("use_llm", False))
        return state
