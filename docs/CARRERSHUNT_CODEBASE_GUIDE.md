# Carrershunt Codebase Architecture and Data Flow Guide

This is the in-repository quick reference that accompanies the detailed DOCX guide.

## Mental model

Carrershunt is a layered job-discovery and candidate-intelligence application:

- **React + Vite** renders the dashboard and makes authenticated API requests.
- **FastAPI** exposes application endpoints, verifies identity, validates inputs, and calls services.
- **SQLAlchemy** persists companies, jobs, ingestion runs/tasks, candidate profiles/evidence, pipeline runs, resume versions, and application/outreach data.
- **Ingestion workers** process the durable company-crawl queue.
- **ATS adapters and a generic crawler** discover and normalize job records.
- **Evidence retrieval + LangGraph** structures job requirements, retrieves candidate evidence, calculates fit/eligibility, and creates a resume plan.
- **Resume quality checks + DOCX service** create a file only after explicit user request.
- **Supabase Auth/profile** supplies login identity and synchronized profile; the SQLAlchemy database is a separate security boundary.

## End-to-end data flow

### 1. Candidate setup
Supabase sign-up/sign-in returns a session. The frontend saves/refreshes the token, synchronizes the Supabase profile, and initializes the local candidate profile. Master resume/profile data is indexed into CandidateEvidence. Optional GitHub sync adds public repository evidence.

### 2. Company ingestion
The user uploads an Excel file to POST /companies/import. The importer reports imported, duplicate, and invalid rows. Company records are upserted, then one IngestionRun and a queued IngestionTask per company are persisted. Workers claim tasks, scrape sources, and update status/count/error fields. The dashboard polls the run endpoint.

### 3. Crawler path
detect_platform() chooses Greenhouse, Lever, Ashby, or generic. Dedicated adapters call public ATS posting APIs. Generic crawling examines JobPosting structured data, eligible detail links, sitemap declarations, linked ATS boards, and optionally Playwright-rendered pages. ingest_company_jobs() validates URLs, strips description HTML, rejects descriptions shorter than 100 characters or the source index itself, and upserts by exact job URL.

### 4. Role analysis
The frontend calls POST /pipeline/{job_id}. The service saves a PipelineRun, invokes the sequential LangGraph path (job intelligence → candidate intelligence/evidence retrieval → match → resume plan), then persists result JSON/status. The analysis stage does not write a DOCX.

### 5. Resume creation
After reviewing the role and analysis, the user explicitly calls POST /resumes/tailor/{job_id}. The route loads a successful plan, applies deterministic claim/quality checks, creates a DOCX, persists a ResumeVersion, and exposes preview/download routes.

### 6. People/outreach/application workflow
Public people search is provided through the configured search integration. Saved people and outreach messages are intended for user review; the app does not claim automatic mass sending. Application routes track per-user status/notes.

## Important files

| File | Purpose |
|---|---|
| app/main.py | FastAPI app, router wiring, lifespan DB setup, embedded local worker loops |
| app/core/auth.py | Current-user/authentication dependency |
| app/core/config.py | Backend configuration |
| app/db/session.py | SQLAlchemy engine, SessionLocal, request DB dependency |
| app/db/models.py | ORM models / relationships |
| app/db/migrations.py | Additive compatibility changes for existing local DBs |
| app/api/routes/companies.py | Excel import, company persistence/listing, ingestion status |
| app/api/routes/jobs.py | Current-workspace jobs listing and one-company crawl enqueue |
| app/api/routes/account.py | Account workspace reset; preserves login and shared records |
| app/api/routes/candidates.py | Candidate profile CRUD and profile evidence |
| app/api/routes/resume_ingestion.py | Master-resume upload/extraction |
| app/api/routes/evidence.py | Evidence listing/retrieval |
| app/api/routes/github.py | Public GitHub ingestion |
| app/api/routes/pipeline.py | Start/read analysis runs |
| app/api/routes/resumes.py | Quality checks, DOCX generation, preview and download |
| app/api/routes/people.py | Public people discovery and related operations |
| app/api/routes/applications.py | Application tracking |
| app/services/company_import.py | Excel workbook parsing/validation |
| app/services/company_store.py | Company upsert |
| app/services/job_sources/base.py | Common JobRecord/JobSource contract |
| app/services/job_sources/factory.py | Platform detection / adapter selection |
| app/services/job_sources/greenhouse.py | Greenhouse public postings API adapter |
| app/services/job_sources/lever.py | Lever public postings API adapter |
| app/services/job_sources/ashby.py | Ashby public postings API adapter |
| app/services/job_sources/generic.py | HTML, JSON-LD, sitemap, linked ATS and Playwright crawler |
| app/services/job_service.py | Validates/cleans/deduplicates jobs before DB persistence |
| app/workers/ingestion_worker.py | Queue claiming, retry/error handling, run/task progress |
| app/services/evidence.py | Candidate evidence fingerprints, upsert and keyword ranking |
| app/services/pipeline_service.py | Persist run, invoke graph, save result |
| app/orchestrator/workflow.py | Sequential LangGraph state graph |
| app/agents/job_agent.py | Structured job requirements |
| app/agents/candidate_agent.py | Relevant candidate evidence context |
| app/agents/match_agent.py | Eligibility and fit/gap result |
| app/agents/resume_agent.py | Evidence-grounded resume plan |
| app/services/resume_quality.py | Deterministic resume claim and quality checks |
| app/services/resume_service.py | DOCX generation |
| frontend/src/App.jsx | UI, auth/session, API calls, dashboard flows |
| frontend/src/styles.css | Styling/responsive layouts |
| tests/test_job_service.py | Valid/invalid job record service tests |
| tests/test_generic_source.py | URL-classifier regression tests |
| tests/test_account_reset.py | Workspace reset/shared data tests |
| .github/workflows/ci.yml | Compile, backend tests, frontend build |

## The latest crawler changes and why

- The generic crawler's _looks_like_job() was too permissive: URLs under broad careers/engineering paths could cause informational pages (benefits, resources, awards, product pages) to be considered role candidates.
- It now favors explicit job-detail URL shapes, excludes recognized listing/resource/product/culture paths, and tests examples resembling Atlassian resource pages and ATS posting/index URLs.
- Generic detail fallback checks the canonical URL before accepting a page.
- The jobs API filters legacy generic rows that fail the URL heuristic, so old bad rows should not be returned in the Jobs response.
- The API filter is a read-time filter: invalid legacy rows are hidden, not physically deleted. Workspace reset or a deliberate cleanup migration is needed to remove eligible unshared old data.
- The heuristic improves precision but cannot recognize every proprietary ATS URL. Add site-specific tests/adapters instead of globally loosening it.

## Database model overview

- Company → many Job and Person.
- IngestionRun → many IngestionTask; tasks point to a company and optionally a job.
- CandidateProfile → many CandidateEvidence and PipelineRun.
- PipelineRun links one candidate and job and stores status/result/error.
- ResumeVersion links candidate/job and records artifact path/content.
- UserApplication is unique per Supabase user + job.
- Legacy Application is global/unique per job; prefer explicit user-scoped semantics in new work.

Company and Job do not have a dedicated Supabase owner column in the inspected schema. Visibility uses ingestion-run/task associations; account reset must preserve data referenced by other accounts/artifacts.

## Runtime and commands

Local:
```powershell
uvicorn app.main:app --reload
cd frontend
npm ci
npm run dev
```

Install the browser runtime used by JavaScript-heavy pages:
```powershell
python -m playwright install chromium
```

API starts four embedded workers by default. For a dedicated worker, set ENABLE_INGESTION_WORKER=false on the API and run:
```powershell
python -m app.workers.ingestion_worker --workers 4
```

Docker Compose has API + dedicated worker + PostgreSQL + Redis, with API embedded workers disabled. The shown worker queue is database-backed; do not assume Redis is the queue implementation.

CI in .github/workflows/ci.yml compiles backend/scripts, runs pytest and builds the Vite frontend. CI does not prove live crawler correctness.

## Known operational caveats

1. job_url should be the external, individual posting URL; /jobs/{id} is Carrershunt's internal UI route and must not be shown as an original external posting.
2. HTTP(S) syntax and URL-shape checks cannot guarantee that an external link is currently open or that its page is truly a job. Manually verify sampled titles, locations, full descriptions, canonical URLs and apply links.
3. Live crawling against the actual Excel file and target sites must be verified separately from unit tests.
4. Supabase profile RLS does not automatically secure the SQLAlchemy DB. Every handler taking a resource ID must verify object-level ownership.
5. The master resume and generated DOCX files currently use local filesystem artifacts; persistent object storage is a production hardening item.
6. app/db/migrations.py is an additive compatibility helper, not a full migration history.
7. Current evidence retrieval is keyword/metadata ranking, not an embeddings/pgvector vector database.

## Recommended next steps

1. Run a small real spreadsheet against one known source in each supported class and manually verify every returned job.
2. Add real sanitized HTML fixtures and source-specific adapters where generic parsing is weak.
3. Add posting URL provenance and URL-check timestamps/results.
4. Audit object-level ownership for all routes (especially people, matches, applications, resume ingestion and settings).
5. Replace ad hoc migrations with versioned migrations and use persistent storage for DB/artifacts.
6. Add per-company crawl yield/rejection reason/duration/freshness metrics.
7. Split the large App.jsx into route/view, API, auth and hook modules.

## Detailed document

The companion Word document Carrershunt_Codebase_Architecture_and_Data_Flow.docx gives the extended architecture explanation, file inventory, detailed data flows, database model, crawler changes and rationale, diagnostics, tests, limitations and roadmap.
