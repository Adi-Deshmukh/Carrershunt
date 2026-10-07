# Carrershunt

AI-powered job discovery, candidate matching, resume tailoring, professional outreach, and application tracking.

## Current backend

- Company Excel ingestion and persistence
- Greenhouse, Lever, Ashby, and generic job ingestion
- Job normalization and deduplication
- Candidate profile/evidence storage
- Deterministic eligibility and skill matching
- Fit score, gaps, explanation, and interview estimate
- AI-grounded tailored DOCX generation
- Public professional profile discovery through a configurable search provider
- Human-reviewed outreach drafting
- Application tracking

## Local setup

1. Create a Python 3.11+ environment.
2. Install the project with the dev dependencies.
3. Copy .env.example to .env.
4. Add OPENAI_API_KEY for AI tailoring.
5. Add SERPER_API_KEY for public-profile discovery.
6. Run the FastAPI server with uvicorn.

The default database is SQLite for local development. Use PostgreSQL in production.

## Workflow

Candidate profile
-> Company Excel
-> Career platform detection
-> Job ingestion
-> Eligibility + matching
-> Tailored resume
-> Public people discovery
-> Outreach draft
-> Application tracking

The system does not automatically send mass outreach. Generated messages remain drafts for user review.
