# Carrershunt Implementation Roadmap

## Status

DONE = implemented. NEXT = immediate work. LATER = deliberately deferred.

## Phase 1 — Candidate Intelligence

| Item | Status |
|---|---|
| Candidate evidence store | DONE |
| Resume parsing and evidence extraction | DONE |
| GitHub ingestion | DONE |
| Candidate-scoped retrieval | DONE |
| Evidence APIs | DONE |

## Phase 2 — Agentic Job-to-Resume Pipeline

| Item | Status |
|---|---|
| LangGraph orchestration | DONE |
| Job Intelligence Agent | DONE |
| Candidate Intelligence Agent | DONE |
| Match Agent | DONE |
| Hard eligibility | DONE |
| Evidence-grounded matching | DONE |
| Resume Agent | DONE |
| Deterministic claim validation | DONE |
| Persistent pipeline runs | DONE |
| DOCX generation | DONE |
| End-to-end pipeline test | DONE |

## Phase 3 — Semantic Matching

| Item | Status |
|---|---|
| Required vs preferred requirement classification | DONE |
| Skill aliases / normalization | DONE |
| Token-level semantic similarity | DONE |
| Hybrid required-skill + semantic score | DONE |
| Evidence-aware candidate representation | DONE |
| Explainable score breakdown | DONE |
| Hard eligibility override protection | DONE |
| Embeddings / pgvector | LATER — add only after retrieval evaluation |
| Historical outcome calibration | LATER |

Phase 3 scoring is intentionally dependency-light. It combines required-skill coverage, preferred-skill coverage, and contextual semantic similarity. Hard eligibility remains deterministic and can cap the score regardless of semantic similarity.

## Phase 4 — Resume Quality and Generation

| Item | Status |
|---|---|
| Evidence-grounded resume plan | DONE |
| Deterministic claim validation | DONE |
| Numeric-claim guard | DONE |
| Placeholder detection | DONE |
| Target-role relevance check | DONE |
| Final quality gate before DOCX persistence | DONE |
| Multiple resume versions per job | DONE |
| Master formatting preservation | NEXT — requires retaining the uploaded source document |
| Persistent object storage | NEXT |
| Rich formatting / ATS layout engine | NEXT |

## People / Outreach — next

| Item | Status |
|---|---|
| Public profile search provider | DONE |
| Public profile discovery | DONE |
| Basic ranking | DONE |
| Contextual job-aware ranking | NEXT |
| Relationship/context signals | NEXT |
| Outreach draft generation | DONE |
| Human review before send | DONE |
| Automatic sending | LATER |

## Productization

| Item | Status |
|---|---|
| React/Vite dashboard | NEXT |
| Authentication / multi-user isolation | NEXT before public SaaS deployment |
| Database migrations | NEXT before production schema changes |
| Background workers | LATER — when volume requires them |
| Scheduled rescans | LATER |
| Redis | LATER |
| Production pgvector | LATER |
| Notifications | LATER |
| Outcome learning | LATER |

## Build order

1. Candidate intelligence.
2. Agentic job-to-resume pipeline.
3. Semantic matching.
4. Resume quality and generation.
5. People contextual ranking.
6. Outreach workflow.
7. React/Vite dashboard.
8. Authentication and production persistence.
9. Outcome collection and calibration.
