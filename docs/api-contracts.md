# API contracts

## Boundary rules

- Browser requests use versioned Next.js Route Handlers.
- Next.js calls FastAPI through server-side internal HTTP requests.
- `AI_SERVICE_BASE_URL` is server-only and is never exposed to browser code.
- Next.js authorizes file and directory selections before ingestion and transfers approved content and metadata; FastAPI must not access arbitrary local paths.
- Next.js applies the final visibility policy to every search response and excludes files whose `app.files.catalog_status` is soft-deleted.

## Initial contract groups

- Health and readiness.
- Authorized file ingestion and processing-status reporting.
- Search requests with normalized query, explicit filters, strategy settings, and bounded result limits.
- Search responses containing file IDs, evidence, scores, retrieval sources, and trace identifiers.
- Cleanup requests keyed by stable file ID, designed to be retryable and idempotent.

The internal FastAPI contract does not grant ownership of application records. FastAPI may create and update only its `ai` tables. Next.js owns `app` tables and remains authoritative for catalog status, file identity, visibility, and access authorization.

## Processing and deletion behavior

Processing responses expose run status without allowing a failed run to replace an active successful run. A cleanup request can be repeated safely after a timeout or partial failure. Historical search, access, and agent events remain available for the initial academic project.
