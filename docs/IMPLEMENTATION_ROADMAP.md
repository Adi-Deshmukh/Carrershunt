# Carrershunt Implementation Roadmap

## Status

DONE = implemented. NEXT = immediate work. LATER = deliberately deferred.

## Foundation

| Item | Status |
|---|---|
| FastAPI | DONE |
| SQLAlchemy | DONE |
| Company Excel import | DONE |
| Greenhouse/Lever/Ashby/generic sources | DONE |
| Job persistence/deduplication | DONE |
| Candidate API | DONE |
| Application tracking | DONE |
| Public people search abstraction | DONE |
| Resume DOCX generation | DONE |
| CI | DONE |
| Database migrations | LATER |

## Candidate intelligence

| Item | Status |
|---|---|
| CandidateEvidence | DONE |
| Resume evidence extraction | DONE |
| GitHub ingestion | DONE |
| Evidence normalization | DONE |
| Retrieval interface | DONE |
| LinkedIn/public profile import | LATER/optional |
| Embeddings | LATER |
| pgvector | LATER |

## Agents

| Item | Status |
|---|---|
| LLM provider abstraction | DONE |
| Agent base | DONE |
| Orchestrator | DONE |
| Job Intelligence Agent | DONE |
| Candidate Intelligence Agent | DONE |
| Match Agent | DONE |
| Resume Agent | DONE |
| People Agent | LATER unless deterministic ranking is insufficient |
| Outreach Agent | LATER; existing service is sufficient |
| Validation Agent | LATER; deterministic validation first |

## Matching

| Item | Status |
|---|---|
| Skill regex matching | DONE |
| Experience eligibility | DONE |
| Education eligibility | DONE |
| Location/work authorization | DONE |
| Structured JD | DONE |
| Evidence-based matching | DONE |
| Semantic matching | NEXT |
| Explainable result | DONE |
| Historical outcome model | LATER |

## Resume

| Item | Status |
|---|---|
| Basic AI tailoring | DONE |
| DOCX generation | DONE |
| Master resume parser | DONE |
| Evidence-grounded tailoring | DONE |
| Claim validation | DONE |
| Preserve master formatting | NEXT |
| Multiple versions | PARTIAL |

## People/outreach

| Item | Status |
|---|---|
| Search provider | DONE |
| Public profile discovery | DONE |
| Basic ranking | DONE |
| Contextual ranking | NEXT |
| Outreach drafts | DONE |
| Automatic sending | LATER |

## Productization

| Item | Status |
|---|---|
| React/Vite dashboard | NEXT after core pipeline |
| Background workers | LATER |
| Scheduled rescans | LATER |
| Redis | LATER |
| Production pgvector | LATER |
| Authentication/multi-user | LATER |
| Notifications | LATER |
| Outcome learning | LATER |

## Build order

1. CandidateEvidence model/service.
2. GitHub ingestion and normalization.
3. LLM provider abstraction.
4. Minimal agent interface and orchestrator.
5. Job Intelligence Agent.
6. Structured job schema and hard eligibility.
7. Match Agent with evidence retrieval.
8. Resume Agent with evidence retrieval.
9. Deterministic claim validator.
10. End-to-end pipeline test.
11. Improve people ranking.
12. Frontend/dashboard.
13. Add embeddings/pgvector only if retrieval quality requires it.
14. Add workers/scheduling only when volume requires them.
