# Database design and ownership

## Local database

The local PostgreSQL 18 + pgvector container is configured in `docker-compose.yml`. It uses the `agentic_files` database and a persistent named volume. Docker configuration and database data are outside migration ownership.

## Schema ownership

The shared PostgreSQL database uses two schemas:

- `app`: owned and migrated by Prisma in Next.js.
- `ai`: owned and migrated by SQLAlchemy/Alembic in FastAPI.

The initial nine tables are:

| Schema | Owner | Tables |
|---|---|---|
| `app` | Next.js/Prisma | `files`, `search_queries`, `search_result_events`, `file_access_events`, `user_preferences` |
| `ai` | FastAPI/Alembic | `file_processing_runs`, `document_chunks`, `chunk_embeddings`, `agent_execution_traces` |

There is no `users` table in the single-user initial design. Next.js generates stable file IDs. AI tables store logical file IDs and do not create foreign keys into `app.files`.

## Lifecycle rules

`app.files.catalog_status` controls visibility and soft deletion. `ai.file_processing_runs.status` controls extraction and indexing lifecycle. After a new run succeeds, one transaction first marks the previous active run superseded, then marks the new run active, and commits. A partial unique index permits only one active run per file; if either update fails, the transaction rolls back and preserves the previous active run. Cleanup of AI records after deletion is explicit, retryable, and idempotent. Historical events are retained.

Changed content keeps the file ID and creates a new processing run. Moves and delete-then-replace operations create new file IDs, and deleted IDs are never reused.

## Migration and shared-object rules

The database administrator performs initial pgvector extension setup. Prisma migrations manage only `app` objects, and Alembic migrations manage only `ai` objects. No cross-schema views or additional database roles are required initially. Vector model and dimension choices remain provisional until benchmarking; redundant embedding dimension metadata is not part of the initial design.
