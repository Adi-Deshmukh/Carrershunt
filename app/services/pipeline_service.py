import json

from app.db.models import CandidateProfile, Job, PipelineRun, ResumeVersion
from app.orchestrator.workflow import pipeline_workflow
from app.schemas.agent import PipelineResult
from app.services.resume_quality import validate_resume_quality
from app.services.resume_service import generate_docx_from_plan


def run_pipeline(db, candidate: CandidateProfile, job: Job, use_llm: bool = False) -> PipelineResult:
    run = PipelineRun(candidate_id=candidate.id, job_id=job.id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    try:
        state = pipeline_workflow.invoke({"db": db, "candidate_record": candidate, "job_record": job, "use_llm": use_llm})
        validation_errors = list(state.get("validation_errors", []))
        resume_id = None
        resume_download_url = None
        resume_generated = False
        if state.get("resume") and not validation_errors:
            quality_errors = validate_resume_quality(
                state["resume"],
                f"{candidate.resume_text or ''} {candidate.experience_years:g}",
                job.title,
            )
            validation_errors.extend(quality_errors)
        if state.get("resume") and not validation_errors:
            path, content = generate_docx_from_plan(candidate, job, state["resume"])
            version = ResumeVersion(job_id=job.id, filename=path.name, content_json=json.dumps(content, ensure_ascii=False), file_path=str(path))
            db.add(version)
            db.flush()
            resume_id = version.id
            resume_download_url = f"/resumes/{version.id}/download"
            resume_generated = True
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
