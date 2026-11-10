# Shared database indexes

No cross-schema indexes are required for the initial nine-table design. Prisma owns indexes on `app` tables, and Alembic owns indexes on `ai` tables, including full-text and pgvector indexes needed by AI retrieval.

Any future index spanning service-owned schemas requires an explicit design review and coordinated migration owner. It is not part of the initial implementation.
