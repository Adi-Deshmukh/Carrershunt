# Carrershunt

AI-powered job discovery, candidate intelligence, job matching, resume tailoring, professional outreach, and application tracking.

## Supabase setup

Carrershunt includes an Auth-backed `public.profiles` table migration and frontend login/signup support.

1. Create/select a Supabase project and apply [the profile migration](supabase/migrations/202610110001_profiles.sql).
2. Copy `frontend/.env.example` to `frontend/.env`; set `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` using the project URL and publishable/anon key.
3. Set `SUPABASE_URL` and `SUPABASE_ANON_KEY` to the same project in the backend `.env`.
4. Configure email/password in Supabase Auth and set Site URL / redirect configuration for your local or deployed frontend.
5. Restart backend and frontend. Test sign-up, sign-in, sign-out, profile write/read, session refresh, and account isolation with two users.
6. Review [the live Supabase and crawler checklist](docs/SUPABASE_AND_CRAWLER_VERIFICATION.md).

Never place a service-role/secret key in frontend variables or commit real credentials.

**Architecture note:** Supabase provides Auth and the synced candidate profile. The current FastAPI application still persists jobs, companies, pipeline runs, and ingestion state through SQLAlchemy. Deployments need a persistent production database; Supabase RLS on `profiles` does not automatically secure the separate backend database.

## Local setup

1. Create a Python 3.11+ environment and install the project with the dev dependencies.
2. Copy `.env.example` to `.env`. Add AI/GitHub/Serper keys as needed.
3. For browser-based crawling, install Playwright Chromium: `playwright install chromium`.
4. Start FastAPI: `uvicorn app.main:app --reload`.
5. Start ingestion workers: `python -m app.workers.ingestion_worker --workers 4`.
6. Start the frontend: `cd frontend && npm ci && npm run dev`.

## Live crawling

Automated tests cover URL validation and ingestion behaviors, but successful discovery against the real company spreadsheet and actual careers sites still needs a live run. Use the verification checklist before marking crawler performance as confirmed.

See `docs/ARCHITECTURE.md`, `docs/IMPLEMENTATION_ROADMAP.md`, and `docs/ASYNC_INGESTION_DESIGN.md`.
