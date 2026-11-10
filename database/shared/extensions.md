# Shared PostgreSQL extensions

The database administrator performs the initial setup of the PostgreSQL extensions required by the approved design, including pgvector. Prisma and Alembic migrations must not independently create or drop shared extensions.

The embedding model and vector dimension remain provisional until benchmarking. The eventual vector column definition must match the selected model configuration.
