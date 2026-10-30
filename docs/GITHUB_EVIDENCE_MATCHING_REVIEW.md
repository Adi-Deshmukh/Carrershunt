# GitHub evidence and matching remediation

## What was changed
- GitHub repository indexing now records richer structured metadata, extracts canonical skills from repository language totals, topics, repository descriptions and README text, and tolerates unavailable README/language endpoints without dropping otherwise indexable repositories.
- Candidate context assembly now includes indexed project evidence as well as lexical matches, so a relevant project can be considered even when its wording differs from the job description.
- Hybrid matching now recognizes common aliases such as JS/JavaScript, Postgres/PostgreSQL, sklearn/scikit-learn, RESTful/REST API, K8s/Kubernetes, and Torch/PyTorch.
- Deterministic resume planning now draws skills and project references from indexed repository evidence and candidate resume content.
- Regression tests cover repository skill extraction, alias matching, evidence retrieval and resume-plan generation.

## Important limitations still requiring work
- JobSpy is not wired into the ingestion architecture. The production crawler currently uses Greenhouse, Lever, Ashby, generic HTML/sitemap parsing and Playwright adapters. Add JobSpy only as an opt-in discovery adapter with rate limits, board-level failure isolation and terms/compliance review; do not assume it can scrape all boards reliably or bypass blocks.
- The GitHub analyzer currently indexes repository metadata and README content, not full source trees, dependency manifests, tests, release history or CI health. A proper comparative analyzer should selectively fetch README, pyproject/package manifests, Docker/compose files, workflow YAML, tests and source entry points, then emit evidence-backed signals with provenance.
- Reference repositories from the task description were not actually supplied as URLs in the current request (the links are scraper libraries, not the selected resume reference repos). Implementing arbitrary repo-vs-repo comparisons needs the user-provided repo list and a defined comparison objective.
- Real-world scraper success still requires running the user-provided Excel and inspecting per-domain crawl output. CI unit tests cannot prove that a given company site currently exposes valid postings.
- Matching remains a heuristic fit score, not a calibrated chance of interview. The API field name interview_estimate is historical and should be relabeled or explained in the UI before users treat it as probability.

## Suggested next architecture slice
1. Source adapters: ATS APIs (Greenhouse/Lever/Ashby) first; company career page crawlers second; optional JobSpy for supported board discovery.
2. Canonical posting normalization: source id, canonical URL, apply URL, title, location, seniority, employment type, full description, posted/updated time, source confidence.
3. Candidate evidence: master resume + profile + curated repo evidence + skills taxonomy; persist every claim with source URL and extraction provenance.
4. Matching: eligibility gates first; taxonomy-normalized required/preferred skills; evidence coverage and seniority/location fit; explain every score component and expose missing requirements separately.
5. Resume tailoring: select only job-relevant, verified evidence; generate a structured diff against the master resume; validate facts/metrics; render into the uploaded DOCX template; compare extracted final DOCX text against the approved plan.
6. Validation: fixture-based tests per ATS, live smoke crawl against a small sample spreadsheet, pipeline API regression, DOCX structure/content tests, and a CI workflow that reports backend and frontend results separately.
