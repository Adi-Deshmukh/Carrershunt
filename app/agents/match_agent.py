from app.services.agent_service import AgentService


class MatchAgent:
    name = "match"

    def __init__(self, service: AgentService | None = None):
        self.service = service or AgentService()

    def run(self, state: dict) -> dict:
        decision, evidence = self.service.match(
            state["db"],
            state["candidate_record"],
            state["job_record"],
            state["job"],
        )
        state["match"] = decision
        state["evidence"] = evidence
        return state
