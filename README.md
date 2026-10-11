# Carrershunt

AI-powered job discovery, candidate intelligence, job matching, resume tailoring, professional outreach, and application tracking.

## Phase 1: Candidate Intelligence

The candidate evidence pipeline:

Candidate profile / master resume → Resume parser → GitHub sync → Candidate Evidence Store → Retrieval service → Evidence supplied to downstream agents.

Implemented:
- Candidate profile creation with automatic evidence indexing.
- Master resume ingestion from PDF, DOCX, or TXT.
- GitHub public profile/repository ingestion.
- Repository metadata, topics, languages, descriptions, and README evidence.
- Candidate-scoped evidence deduplication and relevance-ranked retrieval.
- Evidence inspection and retrieval APIs.
- GitHub rate-limit/token configuration.
- Tests for idempotency, ranking, and candidate isolation.

The retrieval layer is provider-independent. It starts with structured/keyword retrieval and can later add embeddings/pgvector without changing agent interfaces.

## Phase 2: Agentic Job-to-Resume Pipeline

Raw Job → Job Intelligence Agent → Structured JD → Candidate Intelligence Agent → Evidence Retrieval → Match Agent → Hard Eligibility + Evidence-Grounded Fit → Resume Plan + Deterministic Claim Validation → Persistent Pipeline Run → User reviews JD → Explicit Create Resume action → Quality-checked DOCX.

This includes LangGraph orchestration, structured job extraction, evidence-grounded matching, hard eligibility checks, deterministic claim validation, persistent pipeline runs, and user-triggered DOCX generation. Job analysis does not create a DOCX. LLM use is optional; hard eligibility and claim validation remain deterministic.

## Current backend

- Company Excel ingestion and persistence.
- Durable DB-backed ingestion queue with concurrent workers and progress endpoint.
- Greenhouse, Lever, Ashby, generic HTML, sitemap, and Playwright-rendered job ingestion.
- Verified job URLs and description-length validation; placeholder postings are rejected.
- Job normalization and deduplication.
- Candidate evidence storage and retrieval.
- Deterministic eligibility and skill matching.
- AI-grounded tailored DOCX generation on explicit user request.
- Public professional profile discovery and human-reviewed outreach drafts.
- Application tracking.

## Supabase Auth setup

Carrershunt includes an Auth-backed `public.profiles` table migration, session-based login/signup, session refresh/revocation, and candidate-profile initialization.

1. From the repository root, run `python scripts/configure_supabase_env.py`. It creates/updates the root `.env` and `frontend/.env`, preserves other existing settings, and sets the Carrershunt Supabase project values.
2. Restart FastAPI and Vite. Login is fail-closed: the dashboard does not open if the frontend Supabase configuration is missing.
3. Configure email/password under Supabase Auth, then set the Site URL and allowed redirect URLs for localhost and the actual frontend deployment.
4. Run `python scripts/smoke_test_supabase_auth.py` and choose sign-up or sign-in. The script prompts locally for credentials without saving them, then verifies the Auth session and profile read/write. If email confirmation is enabled, confirm the email and rerun in sign-in mode.
5. Test sign-out, session refresh, and account isolation with two accounts. On sign-up/sign-in, the app ensures a Supabase profile row and initializes a local candidate record if one does not exist.
6. Keep generated `.env` files out of Git. The publishable key is intended for browser use; never put a secret/service-role key in any `VITE_*` variable.

See [the Supabase and live crawler verification checklist](docs/SUPABASE_AND_CRAWLER_VERIFICATION.md).

**Data architecture:** Supabase currently provides Auth and the synchronized candidate profile. The API stores normalized companies/jobs and pipeline artifacts through SQLAlchemy. Supabase RLS on `public.profiles` does not automatically secure the separate backend database. Use a persistent production database; container-local SQLite may be lost on redeploy and is unsuitable for multi-instance deployments. Per-account encrypted integration-key storage is not implemented, so integration keys must be configured through the backend environment in account mode.

## Local setup

1. Create a Python 3.11+ environment and install the project with the dev dependencies.
2. Copy `.env.example` to `.env`.
3. Add `GITHUB_TOKEN` for higher GitHub API rate limits (optional for public repositories), AI provider keys for LLM-assisted analysis, and `SERPER_API_KEY` for public-profile discovery.
4. For local JS-rendered careers crawling, install Chromium: `playwright install chromium`.
5. Run FastAPI: `uvicorn app.main:app --reload`.
6. In a second terminal, run the durable crawler workers: `python -m app.workers.ingestion_worker --workers 4`. Keep them running while ingestion tasks are expected to execute.
7. In a third terminal, run the frontend: `cd frontend && npm ci && npm run dev`.

The default database is SQLite for local development. Use PostgreSQL or another persistent SQLAlchemy-supported database for production.

## Phase 1 API flow

- `POST /candidates`
- `POST /candidates/{candidate_id}/resume`
- `POST /candidates/{candidate_id}/github/sync`
- `GET /candidates/{candidate_id}/evidence`
- `POST /candidates/{candidate_id}/evidence/search`

## Product workflow

Candidate intelligence → Company Excel → Career platform detection + source-specific/browser crawling → Verified job ingestion → User clicks Analyze role → Candidate matching + evidence retrieval + resume plan → User reviews the full job description → User clicks Create tailored resume → Quality checks + DOCX download → Public people discovery → Outreach draft → Application tracking.

The system does not automatically send mass outreach. Generated messages remain drafts for user review.

## Live crawler status

Unit tests cover URL validation and ingestion behavior, but successful discovery against the actual company spreadsheet and target careers sites has not yet been verified. Follow the live test checklist rather than treating unit coverage as evidence of successful production crawling.

See `docs/ARCHITECTURE.md`, `docs/IMPLEMENTATION_ROADMAP.md`, `docs/ASYNC_INGESTION_DESIGN.md`, and `docs/CHANGELOG.md`.
