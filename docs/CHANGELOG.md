# Carrershunt Changelog

## Unreleased

### Architecture
- Defined the final lean multi-agent architecture.
- Added an orchestrator as workflow coordinator instead of an autonomous agent swarm.
- Defined RAG as a shared retrieval capability.
- Kept deterministic execution in services and contextual reasoning in agents.
- Deferred vector databases, Redis, workers, autonomous browser agents, microservices, Kubernetes, knowledge graphs and outcome ML until justified.

### Current baseline
- FastAPI API.
- SQLAlchemy persistence with SQLite development configuration.
- Company Excel ingestion.
- Greenhouse, Lever, Ashby and generic job sources.
- Job persistence/deduplication.
- Candidate profile/evidence storage.
- Basic skill/experience/education matching.
- AI resume tailoring and DOCX generation.
- Public professional profile search abstraction.
- Outreach drafting.
- Application tracking.
- GitHub Actions CI.

### Next milestone
Candidate Intelligence + Agent Infrastructure:
- CandidateEvidence model/service.
- GitHub ingestion.
- Retrieval interface.
- Configurable LLM provider abstraction.
- Minimal agent interface.
- Orchestrator.
- Job Intelligence Agent.

Changelog entries should capture product/architecture milestones, while tests accompany affected behavior.
