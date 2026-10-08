import json

from app.db.models import CandidateProfile, Job, PipelineRun, ResumeVersion
from app.orchestrator.workflow import pipeline_workflow
from app.schemas.agent import PipelineResult
from app.services.resume_service import generate_docx_from_plan


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

        validation_errors = state.get("validation_errors", [])
        resume_generated = False
        if state.get("resume") and not validation_errors:
            path, content = generate_docx_from_plan(
                candidate,
                job,
                state["resume"],
            )
            version = ResumeVersion(
                job_id=job.id,
                filename=path.name,
                content_json=json.dumps(content, ensure_ascii=False),
                file_path=str(path),
            )
            db.add(version)
            db.flush()
            resume_generated = True

        result = PipelineResult(
            run_id=run.id,
            candidate_id=candidate.id,
            job_id=job.id,
            status="completed" if not validation_errors else "completed_with_warnings",
            job=state["job"],
            match=state["match"],
            resume=state["resume"],
            resume_generated=resume_generated,
            validation_errors=validation_errors,
        )
        run.status = result.status
        run.result_json = result.model_dump_json()
        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        run.status = "failed"
        run.error = str(exc)[:4000]
        db.add(run)
        db.commit()
        raise
