# Carrershunt Changelog

## Unreleased

### Phase 1 completed
- Added persistent CandidateEvidence records.
- Added PDF, DOCX and TXT master resume extraction.
- Added GitHub profile/repository ingestion with metadata, languages, topics and README content.
- Added candidate-scoped evidence fingerprints and idempotent upserts.
- Added structured keyword/metadata evidence retrieval.
- Added API endpoints for resume ingestion, GitHub synchronization, evidence inspection and retrieval.
- Added tests for idempotency, ranking and candidate isolation.
- Fixed malformed duplicate router wiring in the FastAPI entry point.

### Architecture
- Lean orchestrated multi-agent architecture remains the target.
- RAG is a shared retrieval capability, not a separate agent.
- Deterministic execution remains in services.
- Embeddings/pgvector remain deferred until retrieval quality requires them.

### Next milestone
Agent Infrastructure:
- LLM provider abstraction.
- Minimal agent interface.
- LangGraph workflow.
- Job Intelligence Agent.
