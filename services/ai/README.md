# AI service

FastAPI service for the file recommendation system. Document extraction,
deterministic text chunking, local embeddings, hybrid retrieval, local
cross-encoder reranking, and a bounded search workflow are implemented.

## Setup

From `services/ai`, create and activate the local virtual environment:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and adjust local settings as needed. Set
`AI_DATABASE_URL` to the AI service connection string; its default local target
is the project PostgreSQL container on port 5434.

## Database foundation

The AI service owns only the `ai` PostgreSQL schema. Prisma owns the separate
`app` schema. The initial Alembic migration is intentionally not applied by
service setup:

```powershell
.\.venv\Scripts\alembic.exe upgrade head
```

Apply it only as an explicit database operation after reviewing the migration.

## Run

```powershell
python -m uvicorn app.main:app --reload
```

The health endpoint is available at `http://127.0.0.1:8000/health`.

## Document processing

The extraction pipeline accepts PDF, DOCX, XLSX, CSV, and UTF-8 TXT files. Format
dispatch, extraction, normalization, and chunk generation are separate reusable
components under `app.documents`.

Extraction preserves PDF page numbers, spreadsheet sheet names and cell
coordinates, CSV column names, and DOCX heading context. Normalization is
deterministic: line endings and unnecessary whitespace are normalized while
paragraph boundaries, Unicode, punctuation, and readable table structure are
preserved.

Chunking uses `ChunkConfig(max_characters=1200, overlap_characters=120)` by
default. Chunks have stable sequential ordinals, character counts, optional
source metadata, and no token count until a reliable tokenizer is selected.
Chunking does not select an embedding model or dimension.

Scanned PDFs are not processed with OCR. A PDF with no extractable text raises a
clear extraction error. Corrupted and unsupported files also fail explicitly
rather than silently producing empty content.

## Embeddings

The embedding stage uses the local CPU Sentence Transformers model
`sentence-transformers/all-MiniLM-L6-v2`, which produces 384-dimensional
vectors. The model is loaded lazily once per service configuration and reused;
Sentence Transformers downloads it only when it is absent from the configured
cache.

Configure embedding behavior with `EMBEDDING_MODEL_NAME`,
`MODEL_CACHE_DIR`, `EMBEDDING_BATCH_SIZE`, and `EMBEDDING_DEVICE` in `.env`.
The device must remain `cpu` for this service. Generated vectors are validated
for dimension and finite numeric values before being stored in
`ai.chunk_embeddings`. Persistence is idempotent for the existing
`(chunk_id, model_name, model_version)` uniqueness constraint and runs in a
transaction. Processing-run activation occurs only after generation and
persistence succeed, using the existing activation transaction.

## Hybrid retrieval

`app.retrieval.HybridRetriever` provides keyword, semantic, and combined
retrieval without loading the document collection into Python:

- Full-text retrieval uses PostgreSQL `websearch_to_tsquery`, a `simple`
  `to_tsvector` expression, and `ts_rank_cd` over chunks in `ACTIVE` runs.
- Semantic retrieval embeds the query with the same local model and orders
  pgvector cosine distance over chunks in `ACTIVE` runs.
- Hybrid retrieval fuses the two ranked lists with Reciprocal Rank Fusion:
  `1 / (60 + rank)`, deduplicated by chunk ID. The RRF constant and result
  limit are configurable.

Migration `20261113_0002` adds the matching expression GIN index for full-text
search. It does not add a vector index because the existing dimension-
independent `Vector()` column cannot safely support a fixed-dimension ANN
index.

## Reranking and bounded workflow

`RerankerService` lazily loads the CPU model
`cross-encoder/ms-marco-MiniLM-L-6-v2`, scores query/chunk pairs in batches,
limits candidates, and preserves retrieval metadata while adding a separate
reranking score. Configure it with `RERANKER_MODEL_NAME`,
`RERANKER_BATCH_SIZE`, and `RERANKER_CANDIDATE_LIMIT`.

`AgentWorkflow` executes query normalization, retrieval planning, one of the
allowlisted retrieval tools, reranking, result evaluation, and at most one
refinement. It enforces `WORKFLOW_MAX_TOOL_CALLS`,
`WORKFLOW_TIMEOUT_SECONDS`, and `WORKFLOW_MAX_REFINEMENTS`. Execution traces
store decisions, counts, timings, and summaries in
`ai.agent_execution_traces`; document snippets are not stored in traces.

## Search API

Run the service with:

```powershell
python -m uvicorn app.main:app --reload
```

Endpoints:

- `GET /health`
- `POST /api/v1/search`

Example request:

```json
{
  "query": "architecture decisions about retrieval",
  "limit": 10,
  "retrieval": { "strategy": "hybrid", "rrf_constant": 60 }
}
```

The response contains a trace ID, ranked chunks, file/chunk identifiers,
metadata, retrieval scores, reranking scores, retrieval sources, and a short
explanation. The internal API does not expose database credentials or local
paths.

## Checks

```powershell
ruff check .
ruff format --check .
pytest
```

The retrieval-focused tests can be run with:

```powershell
pytest tests/unit/test_retrieval.py
```
