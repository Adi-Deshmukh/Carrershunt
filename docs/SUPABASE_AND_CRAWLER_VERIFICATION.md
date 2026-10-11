# Supabase and Live Crawler Verification

This checklist is for the live setup, not a statement that these checks have already passed.

## Supabase account setup

1. Create or select the Carrershunt Supabase project.
2. Apply `supabase/migrations/202610110001_profiles.sql` in the Supabase SQL Editor (or with Supabase CLI after linking the project).
3. In project API settings, copy the project URL and the **publishable** key (legacy anon key also works). Never place a secret/service-role key in frontend environment variables.
4. Set the same URL/key pair in both the backend `.env` (`SUPABASE_URL`, `SUPABASE_ANON_KEY`) and `frontend/.env` (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`). Keep `frontend/.env` local; do not commit secrets.
5. Configure Supabase Auth email/password sign-up and the Site URL / redirect allowlist for the actual deployment and localhost used for testing.
6. Restart the backend and frontend. Verify sign-up, sign-out, sign-in, refresh after reload, and an expired-session re-login.
7. Confirm a profile row is created after sign-up. Confirm profile fields persist after update and reload.
8. Test RLS with two separate user accounts: each account must be able to read/update only its own `profiles` row. Anonymous users must not be able to read profile data.
9. After migration, run Supabase security and performance advisors and resolve any exposed-table/RLS warnings.

## Candidate profile vs. local application database

Supabase currently holds Auth identity and the synchronized `public.profiles` row. The API's normalized companies/jobs/pipeline artifacts remain in the local SQLAlchemy database. That database must itself be persistent in deployment; a container-local SQLite file can be lost on redeploy and is not multi-instance storage. Supabase RLS protects `public.profiles`, but does not automatically protect API endpoints or the SQLAlchemy database.

## Live crawler verification

Run this only with a copy of the real company spreadsheet and representative careers URLs you have permission to crawl.

1. Upload the real spreadsheet via Companies → import. Confirm imported, duplicate, and invalid-row counts match a manual spot-check.
2. Confirm queued tasks are picked up by a running ingestion worker (for local setup: `python -m app.workers.ingestion_worker --workers 4`).
3. Use at least one known-good Greenhouse URL, one Lever URL, one Ashby URL, one ordinary HTML careers page, and one JS-rendered page if present in the actual spreadsheet.
4. Inspect each ingestion run/task's status and error fields. For every discovered job, open the canonical job URL and compare title, location, description, and apply URL to the source page.
5. Check that duplicate URL variants do not create duplicate jobs and that blocked, redirecting, invalid, or non-job pages are rejected rather than persisted as jobs.
6. Record per-company counts: expected job pages, discovered, ingested, skipped, failed, and manually confirmed valid. Repeat a crawl to confirm it is idempotent.

## Acceptance criteria

- Signup creates exactly one profile row; profile changes survive a fresh login.
- Two users cannot read or modify each other's profile rows.
- Real spreadsheet ingestion completes through worker processing.
- A manually verified sample of jobs has valid canonical URLs and real descriptions; fabricated placeholder roles are not saved.
- Re-running ingestion does not create duplicate job records.
