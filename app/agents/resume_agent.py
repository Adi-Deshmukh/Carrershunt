from app.services.agent_service import AgentService


class ResumeAgent:
    name = "resume"

    def __init__(self, service: AgentService | None = None):
        self.service = service or AgentService()

    def run(self, state: dict) -> dict:
        plan, errors = self.service.resume_plan(
            state["candidate_record"],
            state["job"],
            state["match"],
            state["evidence"],
            use_llm=state.get("use_llm", False),
        )
        state["resume"] = plan
        state["validation_errors"] = errors
        return state
