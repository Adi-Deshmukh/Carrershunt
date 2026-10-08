# Carrershunt

AI-powered job discovery, candidate intelligence, job matching, resume tailoring, professional outreach, and application tracking.

## Phase 1: Candidate Intelligence

The Phase 1 pipeline is fully connected:

Candidate profile / master resume
  -> Resume parser
  -> GitHub sync
  -> Candidate Evidence Store
  -> Retrieval service
  -> Relevant evidence for downstream agents

Implemented:
- Candidate profile creation with automatic evidence indexing
- Master resume ingestion from PDF, DOCX, or TXT
- GitHub public profile/repository ingestion
- Repository metadata, topics, languages, descriptions, and README evidence
- Candidate-scoped evidence deduplication
- Evidence retrieval with relevance scoring
- Evidence inspection and retrieval APIs
- GitHub rate-limit/token configuration
- Tests for idempotency, ranking, and candidate isolation

The retrieval layer is provider-independent. It starts with structured/keyword retrieval and can later add embeddings/pgvector without changing agent interfaces.

## Current backend

- Company Excel ingestion and persistence
- Greenhouse, Lever, Ashby, and generic job ingestion
- Job normalization and deduplication
- Candidate evidence storage and retrieval
- Deterministic eligibility and skill matching
- AI-grounded tailored DOCX generation
- Public professional profile discovery
- Human-reviewed outreach drafting
- Application tracking

## Local setup

1. Create a Python 3.11+ environment.
2. Install the project with the dev dependencies.
3. Copy .env.example to .env.
4. Add GITHUB_TOKEN for a higher GitHub API rate limit (optional for public repositories).
5. Add OPENAI_API_KEY only if AI tailoring is required.
6. Add SERPER_API_KEY for public-profile discovery.
7. Run FastAPI with uvicorn.

The default database is SQLite for local development. Use PostgreSQL in production.

## Phase 1 API flow

POST /candidates
POST /candidates/{candidate_id}/resume
POST /candidates/{candidate_id}/github/sync
GET /candidates/{candidate_id}/evidence
POST /candidates/{candidate_id}/evidence/search

## Product workflow

Candidate intelligence
-> Company Excel
-> Career platform detection
-> Job ingestion
-> Eligibility + matching
-> Evidence retrieval
-> Tailored resume
-> Public people discovery
-> Outreach draft
-> Application tracking

The system does not automatically send mass outreach. Generated messages remain drafts for user review.

See docs/ARCHITECTURE.md, docs/IMPLEMENTATION_ROADMAP.md, and docs/CHANGELOG.md.
