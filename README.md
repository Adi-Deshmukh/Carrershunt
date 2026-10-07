# Carrershunt

AI-powered job discovery, candidate matching, resume tailoring, and professional outreach.

## Initial architecture

Carrershunt is being built incrementally as a modular pipeline:

1. Import companies from Excel
2. Discover and ingest jobs from career sites/APIs
3. Normalize job descriptions
4. Apply deterministic eligibility rules
5. Match jobs against candidate evidence
6. Generate a grounded tailored resume
7. Discover relevant public professional contacts
8. Generate human-reviewed outreach
9. Track applications and outcomes

## Current phase

Phase 1 establishes the backend foundation and data contracts. The first functional feature will be company Excel ingestion.

## Planned stack

- Python + FastAPI
- PostgreSQL + pgvector
- Redis + background workers
- Playwright for dynamic career pages
- Official job-board APIs where available
- OpenAI API for structured JD analysis, semantic reasoning, and grounded generation
- React + Vite frontend
