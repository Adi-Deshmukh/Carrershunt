from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.candidate_agent import CandidateIntelligenceAgent
from app.agents.job_agent import JobIntelligenceAgent
from app.agents.match_agent import MatchAgent
from app.agents.resume_agent import ResumeAgent


class PipelineState(TypedDict, total=False):
    db: Any
    candidate_record: Any
    job_record: Any
    job: Any
    evidence: list[dict]
    match: Any
    resume: Any
    validation_errors: list[str]
    use_llm: bool


def build_workflow():
    workflow = StateGraph(PipelineState)
    workflow.add_node("job_intelligence", JobIntelligenceAgent().run)
    workflow.add_node("candidate_intelligence", CandidateIntelligenceAgent().run)
    workflow.add_node("match", MatchAgent().run)
    workflow.add_node("resume", ResumeAgent().run)
    workflow.set_entry_point("job_intelligence")
    workflow.add_edge("job_intelligence", "candidate_intelligence")
    workflow.add_edge("candidate_intelligence", "match")
    workflow.add_edge("match", "resume")
    workflow.add_edge("resume", END)
    return workflow.compile()


pipeline_workflow = build_workflow()
