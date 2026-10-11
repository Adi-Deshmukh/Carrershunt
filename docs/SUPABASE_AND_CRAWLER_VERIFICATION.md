# Supabase and Live Crawler Verification

This is an acceptance checklist. A live pass is not claimed until the checks are exercised with the deployed app and the actual company spreadsheet.

## Supabase account setup

1. Use project `carrershunt` in the Mumbai region. Project URL: `https://tqvmfghgficvncyjjxiz.supabase.co`.
2. The profile migration `supabase/migrations/202610110001_profiles.sql` is applied. The table, owner-only RLS policies, signup trigger, and restricted trigger-function privileges were verified using the Supabase database tools.
3. Set `SUPABASE_URL` and `SUPABASE_ANON_KEY` in the backend `.env`. Set the same values as `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` in `frontend/.env`. Use the project's publishable key or legacy anon key only. Do not commit secrets or put a service-role/secret key in frontend variables.
4. In Supabase Auth, enable email/password sign-up and set the Site URL plus allowed redirect URLs for localhost and the deployed frontend.
5. Restart backend and frontend. Verify sign-up, confirmation email if enabled, sign-in, sign-out, token refresh, profile creation and profile update across a fresh login.
6. Use two different accounts to verify that each account can read/update only its own `profiles` row. Verify unauthenticated profile reads/writes are denied.
7. Re-run the Supabase security and performance advisors after any schema change.

## Candidate profile vs. application database

Supabase stores Auth identity and the synchronized `public.profiles` row. Companies, jobs, pipeline runs, resume artifacts, and ingestion state currently live in SQLAlchemy's database. This needs a persistent database in deployment; a container-local SQLite file can be lost on redeploy. RLS on Supabase profiles does not independently protect API endpoints or the separate SQLAlchemy database.

## Live crawler verification

Run using a copy of the actual company spreadsheet and representative careers URLs you are authorized to crawl.

1. If you want to start over, use Companies → Reset my workspace first. This deletes your candidate profile and account-owned ingestion artifacts, and removes company/job records only when no other signed-in account references them. It keeps your login active. Then upload the actual spreadsheet through Companies → Upload Excel. Reconcile imported, duplicate, and invalid-row counts.
2. FastAPI starts four ingestion workers by default for local development. Start the API with `uvicorn app.main:app --reload`; do not also start the standalone worker unless `ENABLE_INGESTION_WORKER=false` is set.
3. Exercise at least one known-good Greenhouse, Lever, Ashby, ordinary HTML careers page, and JavaScript-rendered careers page if present in the real spreadsheet.
4. For each company, inspect ingestion-run/task status and error text. Manually compare discovered job title, canonical URL, location, full description, and apply URL against the source page.
5. Verify invalid URLs, redirected login pages, blocked pages, careers indexes without actual postings, and non-job pages are rejected rather than saved as fake postings. A fresh Excel import marks prior jobs stale before the new crawl when the source is not shared with another signed-in account.
6. Re-run ingestion and verify URL variants do not create duplicate jobs. Record expected, discovered, ingested, skipped, failed, and manually verified-valid counts by company.

## Acceptance criteria

- Signup creates one profile row and profile changes survive signing out and back in.
- Two accounts cannot read or update each other's profile.
- Real spreadsheet ingestion finishes through worker processing.
- A manually reviewed sample of ingested jobs has correct URLs and real descriptions.
- Repeat ingestion is idempotent.
