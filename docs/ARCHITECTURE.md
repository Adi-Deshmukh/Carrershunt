# Carrershunt Architecture

Carrershunt uses a lean, orchestrated multi-agent architecture with retrieval-augmented generation (RAG).

The system is intentionally not a fully autonomous agent swarm. Deterministic application logic remains in normal services; agents are used only where contextual reasoning materially improves the result.

## Final architecture

FastAPI API
  |
Orchestrator
  |
  +-- Job Intelligence Agent -> structured JD
  +-- Candidate Intelligence Agent -> candidate evidence + retrieval
  +-- Match Agent -> eligibility + fit decision
  +-- Resume Agent -> resume strategy/content
  +-- People Agent -> public people discovery/ranking

After resume generation:
Resume Agent -> deterministic claim validation -> Resume Service -> DOCX
People discovery -> Outreach Service -> human-reviewed draft -> Application Tracking

## RAG

Resume, GitHub, LinkedIn/public profile information, projects and achievements are ingested into Candidate Evidence.

Initial retrieval uses structured metadata and keyword matching. Semantic embeddings and pgvector are deliberately deferred until the dataset demonstrates a real retrieval need.

Agents receive only relevant retrieved evidence instead of the entire candidate history. This is critical for free/small model APIs with limited context.

## Agent responsibilities

- Orchestrator: workflow coordination, not autonomous planning.
- Job Intelligence Agent: converts raw JDs into structured requirements; job source services handle crawling/API calls.
- Candidate Intelligence Agent: builds candidate evidence and retrieves relevant evidence.
- Match Agent: combines deterministic hard eligibility with contextual matching; LLM cannot override hard requirements.
- Resume Agent: creates job-specific resume strategy/content from retrieved evidence; never invents facts.
- People Agent: ranks public professional contacts; no private-data scraping or automatic outreach.
- Validation: initially deterministic claim/evidence checking.

## LLM provider

Use a provider abstraction supporting structured JSON, normal text, configurable models, retries/rate limits and safe caching. Do not couple agents to one vendor.

## Deferred infrastructure

Agent swarms, autonomous browser agents, Redis/Celery/RQ, microservices, Kubernetes, dedicated vector databases, knowledge graphs, commit-level GitHub analysis, advanced LinkedIn scraping, fine-tuning, outcome prediction and event buses are not MVP requirements.

## Design rule

If deterministic code can reliably solve it, do not make it an agent. If contextual reasoning over retrieved information is required, use an agent. If infrastructure does not solve a current bottleneck, defer it.
