import json

from app.db.models import CandidateProfile, Job, PipelineRun
from app.orchestrator.workflow import pipeline_workflow
from app.schemas.agent import PipelineResult


def run_pipeline(db, candidate: CandidateProfile, job: Job, use_llm: bool = False) -> PipelineResult:
    run = PipelineRun(candidate_id=candidate.id, job_id=job.id, status="running")
    db.add(run)
    db.flush()

    try:
        state = pipeline_workflow.invoke(
            {
                "db": db,
                "candidate_record": candidate,
                "job_record": job,
                "use_llm": use_llm,
            }
        )
        result = PipelineResult(
            run_id=run.id,
            candidate_id=candidate.id,
            job_id=job.id,
            status="completed" if not state.get("validation_errors") else "completed_with_warnings",
            job=state["job"],
            match=state["match"],
            resume=state["resume"],
            resume_generated=False,
            validation_errors=state.get("validation_errors", []),
        )
        run.status = result.status
        run.result_json = result.model_dump_json()
        db.commit()
        return result
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)[:4000]
        db.commit()
        raise
