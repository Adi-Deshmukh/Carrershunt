import json

from app.db.models import CandidateProfile, Job, PipelineRun, ResumeVersion
from app.orchestrator.workflow import pipeline_workflow
from app.schemas.agent import PipelineResult


def run_pipeline(db, candidate: CandidateProfile, job: Job, use_llm: bool = False) -> PipelineResult:
    run = PipelineRun(candidate_id=candidate.id, job_id=job.id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    try:
        state = pipeline_workflow.invoke({"db": db, "candidate_record": candidate, "job_record": job, "use_llm": use_llm})
        # Analysis produces a validated resume plan, but never creates a DOCX.
        # Artifact generation is an explicit user action on the reviewed job.
        validation_errors = list(state.get("validation_errors", []))
        resume_id = None
        resume_download_url = None
        resume_generated = False
        result = PipelineResult(run_id=run.id, candidate_id=candidate.id, job_id=job.id, status="completed" if not validation_errors else "completed_with_warnings", job=state["job"], match=state["match"], resume=state["resume"], resume_generated=resume_generated, resume_id=resume_id, resume_download_url=resume_download_url, validation_errors=validation_errors)
        run.status = result.status
        run.result_json = result.model_dump_json()
        db.commit()
        return result
    except Exception as exc:
        run_id = run.id
        db.rollback()
        failed_run = db.get(PipelineRun, run_id)
        if failed_run:
            failed_run.status = "failed"
            failed_run.error = str(exc)[:4000]
            db.commit()
        raise
