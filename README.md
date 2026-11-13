# agentic-intelligent-file-recommendation

An Agentic AI-powered file recommendation system using natural-language search,
hybrid PostgreSQL retrieval, local embeddings, bounded cross-encoder reranking,
and personalized recommendations.

## Architecture

The browser communicates only with the Next.js application. `POST /api/search`
validates the request, calls the internal FastAPI `POST /api/v1/search` endpoint,
and filters returned file IDs through Prisma so only ACTIVE catalog files are
shown. FastAPI performs hybrid retrieval over ACTIVE AI processing runs,
reranks candidates locally, evaluates the result set, and records a bounded
execution trace.

The workflow uses one deterministic orchestrator. It permits at most six
allowlisted retrieval/reranking tool calls, one refinement attempt, and a
10-second execution budget. No shell, filesystem, unrestricted SQL, paid API,
or additional autonomous agent is used.

## Local setup

1. Start the project PostgreSQL/pgvector database from `database`.
2. Apply Prisma and AI migrations using the existing project procedures.
3. Configure `services/ai/.env` and `apps/web/.env` from their examples.
4. Start FastAPI from `services/ai` and Next.js from `apps/web`.

The AI service uses CPU-only local models:

- `sentence-transformers/all-MiniLM-L6-v2` for embeddings.
- `cross-encoder/ms-marco-MiniLM-L-6-v2` for reranking.

Models are lazy-loaded and cached locally. The first request may download a
model. API and UI validation commands are documented in the service and web
package manifests.
