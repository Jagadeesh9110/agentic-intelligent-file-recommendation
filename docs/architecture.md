# Hybrid application architecture

## Service boundaries

The application is a single-user, two-service system:

```text
Browser -> Next.js App Router and Route Handlers -> FastAPI AI service
                         |                         |
                         +------ PostgreSQL -------+
```

- Next.js owns the UI, application APIs, file catalog, authorization, visibility, search history, access history, and preferences.
- FastAPI owns extraction, chunking, embeddings, keyword/semantic/hybrid retrieval, reranking, and the bounded agentic workflow.
- The browser never calls FastAPI directly.
- FastAPI never receives arbitrary filesystem paths. Next.js authorizes selected content and transfers approved file content through the internal ingestion contract.

## Database ownership

PostgreSQL uses two service-owned schemas:

- `app`: `files`, `search_queries`, `search_result_events`, `file_access_events`, `user_preferences`; managed by Prisma.
- `ai`: `file_processing_runs`, `document_chunks`, `chunk_embeddings`, `agent_execution_traces`; managed by SQLAlchemy/Alembic.

Next.js generates stable file IDs. AI tables store logical `file_id` values without foreign keys to `app.files`. This preserves ownership boundaries while allowing retrieval to associate chunks with application files.

The database administrator performs initial pgvector extension setup. Prisma and Alembic migrations remain separate. No cross-schema views or additional database roles are required initially.

## File lifecycle

- `app.files.catalog_status` controls application visibility and is authoritative for deletion.
- Deletion is soft deletion. Next.js filters deleted files from every new search response, including when FastAPI cleanup is delayed or fails.
- FastAPI cleanup of chunks, embeddings, and processing data is explicit, retryable, and idempotent.
- Changed content at the same file identity keeps `file_id` and creates a new processing run.
- A moved file, or a file deleted and later replaced at the same path, receives a new file ID. Deleted IDs are never reused.

## Processing activation

A new AI processing run is staged while the previous successful run remains searchable. Only after extraction, chunking, embedding, and persistence succeed does one database transaction:

1. mark the previous active run superseded;
2. mark the new successfully processed run active; and
3. commit the transaction.

A partial unique index permits only one active run per file. If either update fails, the transaction rolls back and the previous active run remains active and searchable.

Failed or incomplete runs cannot make a previously active version unavailable.

Processing runs use the statuses `QUEUED`, `PROCESSING`, `ACTIVE`, `SUPERSEDED`,
`FAILED`, and `CANCELLED`.
