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
| LLM provider abstraction | NEXT |
| Agent base | NEXT |
| Orchestrator | NEXT |
| Job Intelligence Agent | NEXT |
| Candidate Intelligence Agent | NEXT |
| Match Agent | NEXT |
| Resume Agent | NEXT |
| People Agent | LATER unless deterministic ranking is insufficient |
| Outreach Agent | LATER; existing service is sufficient |
| Validation Agent | LATER; deterministic validation first |

## Matching

| Item | Status |
|---|---|
| Skill regex matching | DONE |
| Experience eligibility | DONE |
| Education eligibility | DONE |
| Location/work authorization | NEXT |
| Structured JD | NEXT |
| Evidence-based matching | NEXT |
| Semantic matching | NEXT |
| Explainable result | NEXT |
| Historical outcome model | LATER |

## Resume

| Item | Status |
|---|---|
| Basic AI tailoring | DONE |
| DOCX generation | DONE |
| Master resume parser | NEXT |
| Evidence-grounded tailoring | NEXT |
| Claim validation | NEXT |
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
