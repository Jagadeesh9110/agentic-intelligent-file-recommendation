# Agentic AI-Based Intelligent File Recommendation

## Project Plan

**Repository:** `agentic-intelligent-file-recommendation`  
**Document status:** Initial planning baseline  
**Project stage:** Pre-implementation

> This document separates confirmed requirements from proposed design decisions. The project description and requested technology areas are confirmed inputs; technology versions, UI details, deployment choices, and production-scale features remain design decisions to validate during implementation.

## 1. Problem Definition

### 1.1 Problem statement

Users often have many documents distributed across folders and file types. Traditional file search depends heavily on exact filenames, remembered locations, and manually chosen filters. It does not reliably understand the meaning of a natural-language request such as “find the budget proposal discussed last quarter” or “show the design documents related to authentication.”

The project will design and implement a system that lets a user search for files using natural language and receive relevant, explainable recommendations. It will combine lexical matching, semantic retrieval, adaptive retrieval decisions, and limited personalization while preserving query relevance and user privacy.

### 1.2 Limitations of traditional file search

- Exact filename and keyword dependence.
- Weak understanding of synonyms, paraphrases, and document meaning.
- Poor results when the user remembers content but not location.
- Limited support for mixed file formats and extracted text.
- Ranking based mostly on filename, path, or modification time.
- No principled combination of keyword and semantic evidence.
- Little use of prior user interactions to improve ranking.
- No transparent explanation of why a file was recommended.

### 1.3 Motivation

Natural-language file discovery can reduce time spent browsing folders and improve access to information that is already available but difficult to locate. The project is also a suitable academic study because it permits measurable comparisons among keyword, semantic, hybrid, reranked, and adaptive retrieval approaches.

### 1.4 Proposed solution

The proposed system will:

1. Register files from approved local or configured source directories.
2. Extract searchable text and metadata from supported formats.
3. Split extracted content into searchable chunks.
4. Generate embeddings for chunks and store them in PostgreSQL with pgvector.
5. Execute keyword and semantic retrieval for a natural-language query.
6. Fuse ranked lists with Reciprocal Rank Fusion (RRF).
7. Optionally rerank a small candidate set with a cross-encoder.
8. Use a bounded agentic workflow to select retrieval tools, assess results, retry when appropriate, and record its trace.
9. Apply conservative personalization using search history, access history, and explicit preferences.
10. Present results with relevance explanations and basic source metadata.

### 1.5 Objectives

- Build a working natural-language file search prototype.
- Compare keyword, semantic, hybrid, reranked, and adaptive retrieval.
- Establish an evaluation dataset and report Precision@K, Recall@K, MRR, NDCG, and latency.
- Demonstrate agentic orchestration through tool selection, evaluation, bounded retry, and traceability.
- Keep the system understandable, testable, privacy-aware, and achievable as an academic capstone.

## 2. Requirements Analysis

### 2.1 Target users

- **Initial target:** one individual user searching a locally configured document collection.
- **Demonstration target:** a student or researcher managing project materials on one machine.

The initial system is explicitly single-user. Multi-user accounts, shared collections, roles, and authentication are not required for the capstone unless deployment or evaluation demonstrates a genuine need. The initial version is not intended to be a multi-tenant enterprise document-management platform.

### 2.2 Functional requirements

**File and ingestion**

- Register supported files from an approved source.
- Detect file type and collect filename, path, size, timestamps, and checksum.
- Extract text from PDF, DOCX, XLSX/CSV, and plain text files where supported.
- Record extraction status and an actionable failure reason.
- Chunk extracted text with stable chunk positions.
- Re-index a file when its checksum changes.
- Avoid duplicate indexing when the content has not changed.

**Search and recommendations**

- Accept a natural-language query.
- Support optional filters such as file type, source, date range, and folder.
- Retrieve keyword matches using PostgreSQL full-text search.
- Retrieve semantic matches using vector similarity.
- Fuse lexical and semantic results with RRF.
- Optionally rerank a bounded candidate set.
- Return file-level results even when matching evidence is at chunk level.
- Show matched snippets, basic metadata, and a concise relevance explanation.
- Allow the user to open or copy the configured file location subject to access controls.

**Agent workflow and personalization**

- Classify query intent and identify useful filters.
- Select among deterministic retrieval tools.
- Evaluate whether results are sufficient according to explicit thresholds.
- Retry with an alternate query expansion or retrieval strategy within a fixed budget.
- Record decisions, tools, timings, and result counts in an execution trace.
- Use prior interactions and preferences as weak ranking signals.
- Allow users to clear or disable personalization data.

**Administration and observability**

- Report indexing progress and failures.
- Expose health and readiness information.
- Provide basic search and ingestion operational logs without logging document contents by default.

### 2.3 Non-functional requirements

- **Correctness:** Search results must be traceable to indexed files and chunks.
- **Performance:** Establish a measurable prototype target, for example p95 search latency under 2 seconds for a small evaluation corpus, then revise based on evidence.
- **Reliability:** A failed file must not prevent other files from indexing; failures must be visible.
- **Security:** Validate paths, prevent unauthorized file access, and protect stored user data.
- **Privacy:** Do not send document content to external model providers in the initial design.
- **Maintainability:** Prefer a modular monolith and explicit interfaces over premature services.
- **Testability:** Retrieval components, parsing, orchestration, APIs, and evaluation must be independently testable.
- **Explainability:** Results should expose retrieval sources and high-level ranking reasons.
- **Reproducibility:** Record model names, preprocessing settings, and evaluation dataset versions.

### 2.4 Representative use cases

1. A user searches “meeting notes about database migration” and receives relevant files even when the phrase is absent from filenames.
2. A user searches for “the spreadsheet with quarterly expenses” and restricts results to spreadsheets and a date range.
3. A user indexes a new PDF; the system extracts text, creates chunks and embeddings, and makes it searchable.
4. A user opens a recommended file; the system records access history if the user has enabled it.
5. A vague query initially produces weak results; the workflow tries a semantic or hybrid strategy and reports the final trace.
6. A user disables personalization and receives results ranked only by query and configured filters.
7. An administrator reviews files that failed extraction and retries them after correcting the source.

### 2.5 System constraints

- The initial corpus target is approximately **300–500 files** (primarily PDF, DOCX, XLSX/CSV, and plain text), producing an expected range of roughly 5,000–20,000 searchable chunks. This is large enough to expose retrieval differences while remaining suitable for a single-machine academic prototype.
- The initial evaluation set will contain **40 fixed natural-language queries** over that corpus, with manually judged graded relevance for the top candidate files. The set will include approximately 10 queries each for exact terms, paraphrases/concepts, ambiguous requests, and filter/rare-term cases.
- Supported formats and extraction quality will be limited by selected libraries.
- The embedding model and cross-encoder must run within available local CPU/GPU and memory limits.
- File access is limited to one explicitly configured directory tree and the single user’s local permissions.
- The first release will use one backend deployment and one PostgreSQL database.
- Evaluation relevance labels will be created manually and may not represent every user population.

### 2.6 Security and privacy requirements

- Restrict ingestion to allowlisted roots; normalize and validate every path.
- Do not allow a search result to expose a file outside the user’s permitted roots.
- Use parameterized queries and framework validation for all API inputs.
- Store passwords only if authentication is added; use a proven password-hashing library.
- Avoid storing full document contents in logs, traces, or analytics.
- Encrypt transport in deployed environments and protect database credentials through environment configuration.
- Treat extracted content and embeddings as sensitive; embeddings can still reveal information.
- Provide retention and deletion behavior for indexed content, histories, traces, and embeddings.
- Define whether file access is authoritative or advisory; the initial implementation must fail closed when access cannot be verified.

## 3. Scope Definition

### 3.1 Core features

- Single-user file collection.
- Explicit manual ingestion from a user-selected file or a user-selected configured directory scan; no background file watcher is required initially.
- PDF, DOCX, XLSX/CSV, and plain-text extraction.
- Metadata and checksum tracking.
- Chunking and local embedding generation.
- PostgreSQL full-text, pgvector semantic, and RRF hybrid retrieval.
- Natural-language search with basic filters.
- Bounded agentic orchestration with deterministic tools and execution trace.
- Basic search/access history and opt-in personalization for the single user.
- Offline evaluation dataset and reproducible retrieval metrics.

### 3.2 Important additional features

- Incremental re-indexing and deletion synchronization.
- Search result snippets and evidence chunks.
- Indexing status and failure dashboard.
- Query expansion for terms and file-type hints.
- Configurable relevance thresholds and retry budget.
- Bounded cross-encoder reranking.
- Exportable evaluation results.

### 3.3 Optional features

- OCR for scanned PDFs.
- File watching instead of explicit ingestion.
- AI-assisted query interpretation and strategy selection using a local or otherwise approved model.
- Multiple user roles and shared collections.
- Authentication for a deployment that moves beyond the trusted single-user machine.
- Feedback buttons for relevance labels.
- Explainable score breakdown in the UI.
- Additional embedding or reranker models for experiments.
- Cloud object storage connectors.

### 3.4 Explicitly excluded from the initial project

- Autonomous agents that modify, move, delete, or summarize files without confirmation.
- General-purpose conversational assistant unrelated to file retrieval.
- Multiple cooperating autonomous agents.
- Microservices, event buses, and distributed workflow engines.
- Enterprise identity federation, legal hold, and compliance certification.
- Public web crawling and external search.
- Automatic OCR and support for every office or media format.
- Training a foundation model or fine-tuning a large language model.
- Fully autonomous relevance labeling.
- Production-scale multi-region deployment.

## 4. Technology Stack Evaluation

### 4.1 Frontend

| Technology | Purpose and value | Alternatives | Assessment |
|---|---|---|---|
| Next.js | React-based UI, routing, and a maintainable TypeScript application shell | React with Vite, server-rendered templates, or a simple HTML client | Reasonable if a polished UI is required; its server features should not duplicate the FastAPI backend. |
| TypeScript | Static checking for UI state, API contracts, and result rendering | JavaScript | Recommended for maintainability. |
| Tailwind CSS | Rapid consistent styling for a search-oriented prototype | CSS modules, plain CSS, or a component library | Optional; use only if the team is comfortable with it. Plain CSS is simpler for a small UI. |

**Recommendation:** Next.js, TypeScript, and Tailwind CSS if the project includes a modern UI. Keep business logic and data access in FastAPI rather than Next.js route handlers.

### 4.2 Backend

| Technology | Purpose and value | Alternatives | Assessment |
|---|---|---|---|
| Python | Strong ecosystem for NLP, parsing, evaluation, and experimentation | Node.js or Java | Recommended because the retrieval and file-processing ecosystem is Python-centric. |
| FastAPI | Typed HTTP API, validation, and interactive API documentation | Flask, Django REST Framework | Recommended for a focused API; Django would add unnecessary framework surface. |
| SQLAlchemy | Database models, queries, and transaction management | SQLModel, asyncpg directly, Django ORM | Recommended if relational modeling and portability matter. SQLModel can reduce boilerplate but is an additional abstraction choice. |
| Pydantic | Request/response validation and configuration models | Dataclasses plus manual validation | Recommended through FastAPI. |

### 4.3 Database and search

| Technology | Purpose and value | Alternatives | Assessment |
|---|---|---|---|
| PostgreSQL | Durable metadata, histories, filters, and transactions | SQLite for a single-user prototype | Recommended if pgvector and full-text search are part of the study. SQLite is simpler but changes the intended hybrid-search experiment. |
| pgvector | Stores and searches chunk embeddings in PostgreSQL | FAISS, Chroma, Qdrant, Elasticsearch/OpenSearch | Recommended for one integrated persistence layer. A separate vector database is unnecessary initially. |
| PostgreSQL full-text search | Lexical retrieval and ranking | SQLite FTS5, Elasticsearch/OpenSearch | Recommended for consistency with the primary database. |
| Alembic | Versioned schema migrations | Manual SQL scripts, Django migrations | Recommended with SQLAlchemy; migration history is important even for a capstone. |

### 4.4 AI, retrieval, and processing

| Technology | Purpose and value | Alternatives | Assessment |
|---|---|---|---|
| Sentence Transformers | Local embedding and cross-encoder inference | Hosted embedding APIs, scikit-learn TF-IDF | Recommended for local semantic search and privacy. TF-IDF is a useful baseline, not a replacement for embeddings. |
| `all-MiniLM-L6-v2` | Small, fast general-purpose embedding baseline | E5-small, BGE-small, hosted models | A reasonable starting model; benchmark it rather than treating it as universally optimal. |
| RRF | Combines independent ranked lists without incompatible score calibration | Weighted score normalization, learning-to-rank | Recommended because it is simple, explainable, and suitable for a capstone. |
| Cross-encoder reranker | Improves ordering of a small candidate set using query-document interaction | No reranking, cosine-score weighting, learned ranker | Optional but valuable for evaluation; cap candidate count to control latency. |
| Custom Python workflow | Makes tool selection, evaluation, retries, and traces explicit | Fixed pipeline, LangGraph, other orchestration frameworks | Recommended initially. A framework is unnecessary until workflow state or persistence becomes complex. |
| LLM | Optional query interpretation or explanation | Deterministic parser and templates | Not required for the core system. If added, constrain it to query understanding and explanation, never direct unrestricted file access. |
| PyMuPDF | PDF text and metadata extraction | pypdf, Apache Tika | Recommended for local PDF extraction; scanned PDFs remain an optional OCR concern. |
| `python-docx` | DOCX paragraph/table extraction | Mammoth, Apache Tika | Recommended for the requested scope. |
| pandas/openpyxl | Spreadsheet and CSV extraction | Python `csv`, calamine | pandas is useful for tabular normalization but may be excessive for very simple CSV handling; openpyxl is appropriate for XLSX. |

### 4.5 Testing and tooling

| Technology | Purpose and value | Alternatives | Assessment |
|---|---|---|---|
| pytest | Unit, integration, and evaluation test runner | unittest | Recommended. |
| Postman | Manual API exploration and saved examples | OpenAPI UI, curl, HTTP client tests | Useful during development but not a substitute for automated tests. FastAPI’s generated OpenAPI docs may be sufficient. |
| Git/GitHub | Version control, collaboration, and review | Other hosted Git platforms | Confirmed and recommended. |

### 4.6 Final recommended stack

- **Frontend:** Next.js + TypeScript + Tailwind CSS.
- **Backend:** Python + FastAPI + Pydantic + SQLAlchemy.
- **Database:** PostgreSQL + pgvector + PostgreSQL full-text search + Alembic.
- **Processing:** PyMuPDF, python-docx, pandas/openpyxl, and plain-text readers.
- **Retrieval:** Sentence Transformers with `all-MiniLM-L6-v2` as the first embedding baseline, RRF, and an optional cross-encoder.
- **Agent workflow:** A custom bounded Python orchestration module with explicit tools and trace records.
- **Testing:** pytest, API contract tests, and optional Postman collections.
- **Deployment:** Start as a single-machine modular monolith. Add a background worker only when ingestion duration or reliability demonstrates the need.

## 5. System Architecture

### 5.1 Architectural style

Use a modular monolith:

```text
+------------------+       HTTP/JSON        +-----------------------------+
| Next.js frontend | <--------------------> | FastAPI application          |
| Search UI        |                         | API + orchestration          |
| Ingestion UI     |                         | retrieval + personalization  |
+------------------+                         +---------------+-------------+
                                                           |
                                      +--------------------+--------------------+
                                      |                                         |
                              +-------v--------+                        +-------v--------+
                              | PostgreSQL      |                        | Local file roots |
                              | metadata       |                        | approved inputs |
                              | FTS + pgvector |                        +-----------------+
                              +----------------+
```

The backend is divided into modules, not separately deployed services:

- API and authentication boundary.
- File catalog and ingestion coordinator.
- Format-specific extraction adapters.
- Chunking and embedding pipeline.
- Keyword, semantic, fusion, and reranking retrieval modules.
- Agent workflow and trace recorder.
- Personalization and history module.
- Evaluation and administration utilities.

### 5.2 File ingestion and content extraction

The initial ingestion method is an explicit user-triggered scan: the single user selects one approved file or directory in the UI (or supplies it through the API), and then starts ingestion. The service scans only that selection and its allowed descendants; it does not watch the file system continuously and does not ingest arbitrary paths.

1. The user selects an approved source directory or file and starts an ingestion job.
2. The ingestion coordinator validates the path and computes a checksum.
3. The file catalog creates or updates the file record.
4. A format adapter extracts text and normalized metadata.
5. Extraction status, warnings, and failures are stored.
6. The chunker creates stable chunks with source offsets or page/sheet context.
7. The embedding component generates vectors in batches.
8. A transaction stores chunks, embeddings, and searchable text.
9. Re-indexing replaces stale chunks only after the new extraction succeeds.

For the target 300–500-file corpus, the first implementation may run the scan as a bounded background task so the UI remains responsive; a separate worker service is not required. The design should expose an ingestion interface so a durable worker can be added later without changing the API contract. Re-indexing is explicit or triggered by a later scan that detects a changed checksum.

### 5.3 Retrieval flow

1. Validate the query and filters.
2. Normalize the query and identify explicit constraints.
3. The workflow chooses keyword, semantic, or hybrid retrieval.
4. Keyword retrieval searches PostgreSQL full-text indexes.
5. Semantic retrieval embeds the query and searches pgvector.
6. Hybrid retrieval fuses ranked candidates using RRF.
7. A cross-encoder optionally reranks only the top candidate set.
8. Chunk scores are aggregated to file-level results.
9. Personalization provides bounded tie-breaker or boost signals.
10. The response includes results, evidence, timings, and a trace identifier.

### 5.4 Component communication

- Frontend to backend: versioned JSON HTTP APIs.
- Backend to PostgreSQL: SQLAlchemy transactions and parameterized queries.
- Backend to file system: allowlisted, validated local paths through an ingestion/access adapter.
- Backend to embedding models: local Python inference interface.
- Backend modules: typed Python interfaces and domain objects rather than direct cross-module database access.

## 6. Database Design

The initial schema should remain small and normalized. Embeddings belong to chunks because different portions of one file have different meanings.

### 6.1 Entities

**users**

- `id`, display name, status, timestamps.

The initial deployment has one seeded local user and no login flow. An authentication identifier and additional users are deferred until multi-user support becomes an explicit requirement.

**files**

- `id`, owner or collection reference, canonical relative path, filename, extension, MIME type, size, checksum, created/modified timestamps, extraction status, indexing status, error summary, timestamps.

**file_chunks**

- `id`, `file_id`, chunk ordinal, page/sheet/section metadata, extracted text, normalized search text, token or character counts, timestamps.

**chunk_embeddings**

- `chunk_id`, model name/version, vector, embedding dimensions, created timestamp.

An embedding may be stored in the chunk table if only one model is ever supported. A separate table is preferable for model comparison and controlled re-indexing.

**search_queries**

- `id`, `user_id` nullable for single-user mode, raw query or privacy-safe representation, normalized query, filters, selected strategy, trace id, created timestamp.

Do not retain raw queries indefinitely without a retention decision.

**search_result_events**

- `id`, `search_query_id`, `file_id`, rank, score, retrieval sources, clicked/opened flag, created timestamp.

This supports evaluation of interaction signals without duplicating complete result payloads.

**file_access_events**

- `id`, `user_id`, `file_id`, action, timestamp, success indicator.

**user_preferences**

- `user_id`, preference key/value or typed preference columns, personalization enabled flag, timestamps.

### 6.2 Relationships

- One user can own or access many files.
- One file has many chunks.
- One chunk can have one embedding per embedding model.
- One user can create many search queries.
- One search query can produce many result events.
- One user can create many file access events.
- A user has one preference record or a small set of typed preference records.

### 6.3 Tables deliberately not included initially

- Separate sessions table unless authentication requires it.
- Separate recommendation table; recommendations are derived from query results and recorded through result events.
- Separate agent table; workflow traces can be stored in a trace JSON field or a small trace-event table only if observability requires durable querying.
- Separate vector database schema; pgvector is sufficient for the initial scale.

## 7. Agentic AI Design

### 7.1 What makes the system agentic

The agentic behavior is a bounded decision loop around retrieval, containing a constrained AI-assisted decision-making component alongside deterministic safeguards:

- It interprets the query and constraints.
- It selects from available retrieval tools through a structured decision.
- It observes candidate quality signals.
- It decides whether another allowed strategy is warranted.
- It stops when a success criterion or retry budget is reached.
- It records its decisions and evidence.

Vector search by itself is not agentic AI. A fixed sequence of embedding, nearest-neighbor search, and response formatting is a retrieval pipeline. The agentic claim is justified only by explicit state, tool selection, evaluation, adaptive retry, and traceability.

### 7.2 Proposed responsibilities

Use one orchestrator with specialized deterministic tools rather than multiple autonomous agents:

- **Query understanding:** normalize text, identify filters, detect likely file types, and optionally produce a constrained query representation.
- **AI-assisted decision component:** when an approved local model is available, receive only the normalized query, parsed filters, corpus capability summary, and prior retrieval signals; return a schema-constrained choice of `keyword`, `semantic`, `hybrid`, `rerank`, or `retry`, plus a short reason code and confidence. It cannot access files directly, invent paths, write to the database, or select tools outside an allowlist.
- **Strategy selection:** combine the AI-assisted proposal with deterministic rules. Exact identifiers and explicit filters can force keyword retrieval; empty or weak results can force a permitted fallback; low confidence always falls back to hybrid.
- **Keyword retrieval tool:** execute full-text search with filters.
- **Semantic retrieval tool:** embed the query and execute vector search.
- **Hybrid retrieval tool:** call both ranked retrievers and apply RRF.
- **Reranking tool:** apply the cross-encoder to a bounded candidate set.
- **Result evaluator:** inspect candidate count, score separation, duplicate rate, and threshold signals.
- **Personalization tool:** calculate conservative preference and history features.
- **Recommendation formatter:** produce results, evidence, explanations, and trace metadata.

### 7.3 Deterministic rules versus AI-assisted reasoning

**Deterministic and preferred for the first implementation**

- Filter parsing for dates, extensions, and explicit folders.
- Allowlisted structured decision schema and tool names.
- Retrieval tool interfaces.
- RRF computation.
- Candidate limits and retry budgets.
- Result sufficiency thresholds.
- Access checks, path validation, and authorization.
- Score aggregation and personalization caps.
- Trace persistence.

**Constrained AI-assisted behavior**

- Query intent classification and strategy proposals when deterministic rules are insufficient.
- Controlled query expansion and synonym suggestions, limited to a small validated term list.
- Natural-language explanation of already-selected evidence, grounded only in returned snippets.

The AI-assisted component is not a security or authorization boundary and does not replace measurable retrieval logic. Its output must conform to a schema, pass enum, length, confidence, and candidate-limit validation, and be logged as a proposal before safeguards approve it. Deterministic rules can veto or replace every proposal. If the approved local model is unavailable, the same workflow must continue with deterministic strategy selection. External model calls and document-content transmission are excluded from the initial privacy-preserving design.

### 7.4 Adaptive workflow

```text
Receive query
  -> validate and normalize
  -> parse explicit filters
  -> select initial strategy
  -> retrieve candidates
  -> evaluate sufficiency
       -> sufficient: rerank/format/return
       -> insufficient and budget remains: alter strategy or expand query
       -> insufficient and budget exhausted: return best results with explanation
  -> persist trace and interaction metadata
```

The workflow should have a small maximum number of attempts, for example two or three, and a time budget. Every retry must use a materially different allowed strategy; repeating the same search is not adaptation. The acceptance test for agentic behavior is that the trace shows a valid proposal or deterministic decision, safeguard outcome, tool execution, evaluation signal, and bounded termination reason.

### 7.5 Execution trace

Record:

- Trace and query identifiers.
- Normalized query and non-sensitive filter representation.
- Selected strategy and reason code.
- Tool names, inputs after redaction, candidate counts, and timings.
- Evaluation signals and retry decisions.
- Model identifiers.
- Final result count and termination reason.

Do not store full document text or unrestricted model prompts in traces by default.

## 8. Retrieval Architecture

### 8.1 Keyword retrieval

Normalize extracted text and use PostgreSQL full-text search with a stored search vector and appropriate indexes. Search should cover chunk text and selected metadata. Exact filename and path matches can receive a controlled boost, but should not overwhelm content relevance.

### 8.2 Semantic retrieval

Generate a query embedding using the same model family used for indexed chunks. Retrieve nearest chunks with pgvector, apply metadata filters, and aggregate chunk evidence to files. Record model and distance configuration so experiments are reproducible.

### 8.3 Hybrid retrieval

Run lexical and semantic retrieval independently, retain ranked lists, and combine them. Hybrid retrieval is expected to be the default because it handles both exact identifiers and conceptual language.

### 8.4 Reciprocal Rank Fusion

For a result `d` across ranked lists, use:

`RRF(d) = sum over lists of 1 / (k + rank(list, d))`

where `k` is a fixed smoothing constant. The implementation must define whether ranks start at one, how duplicate chunks map to one file, and how ties are handled. RRF is preferred over adding raw BM25 and vector scores because those scores are not naturally calibrated.

### 8.5 Cross-encoder reranking

Apply a cross-encoder only to a limited candidate list after fusion. The model receives the query and candidate text and returns a relevance score. This improves ordering at additional latency and should be feature-flagged for comparison. The response should distinguish retrieval scores from reranker scores.

### 8.6 Retrieval evaluation

Create and version one fixed gold dataset containing:

- The target corpus of approximately 300–500 permitted documents.
- 40 representative natural-language queries, maintained in a versioned JSON or CSV fixture.
- At least one graded relevance label per query-document pair: irrelevant, partially relevant, highly relevant.
- Query categories such as exact terms, paraphrases, ambiguous queries, filters, and rare terms.
- A documented corpus manifest containing file identifiers, content checksums, supported format, and exclusion reasons.
- A documented annotation guide and manually reviewed relevance judgments; documents and labels must not contain confidential material.

Compare:

1. Keyword only.
2. Semantic only.
3. Hybrid with RRF.
4. Hybrid plus cross-encoder.
5. Adaptive workflow with and without personalization.

The evaluation runner must use a pinned corpus manifest, query/label version, model identifiers, embedding dimensions, chunk size and overlap, retrieval top-K values, RRF constant, reranker setting, database/index configuration, and random seeds where applicable. It must export the configuration, per-query ranked results, metric values, stage timings, and software revision together. Results are not comparable across runs when any of these inputs changes; such changes require a new evaluation version.

## 9. Personalization Design

Personalization must improve discovery without overriding the current query.

- Search history can identify recurring topics, preferred file types, and recent work areas.
- File access history can provide a small recency/frequency signal for files the user already uses.
- Explicit preferences can include preferred extensions, folders, or a personalization opt-out.
- Personalization should be applied after query relevance and hard access/filter constraints.
- Use capped boosts or tie-breaking rather than replacing relevance scores.
- A highly relevant new file must outrank a frequently accessed but weakly matching file.
- Avoid inferring sensitive attributes from behavior.
- Explain when a preference or history signal affected ordering, if the UI exposes score explanations.
- Provide clear disable, clear-history, and retention controls.

An initial scoring policy can reserve most ranking weight for retrieval relevance and apply a small bounded personalization adjustment. The exact coefficient must be evaluated rather than assumed.

## 10. API Planning

These are planned contracts, not implementations.

### 10.1 Health and configuration

- `GET /health` — liveness.
- `GET /ready` — readiness for database and model dependencies.
- `GET /api/v1/config/capabilities` — supported file types and enabled retrieval features.

### 10.2 File catalog and ingestion

- `POST /api/v1/files/scan` — scan an approved source and discover changes.
- `POST /api/v1/files` — register or ingest a selected file.
- `GET /api/v1/files` — list files with status and filters.
- `GET /api/v1/files/{file_id}` — file metadata and indexing status.
- `POST /api/v1/files/{file_id}/reindex` — request re-indexing.
- `DELETE /api/v1/files/{file_id}` — remove indexed representation and history according to retention rules.
- `GET /api/v1/ingestion/jobs/{job_id}` — progress, warnings, and failures.

### 10.3 Search and recommendations

- `POST /api/v1/search` — execute a query with filters and optional strategy controls.
- `GET /api/v1/search/{trace_id}` — retrieve a trace or result metadata subject to privacy policy.
- `GET /api/v1/files/{file_id}/evidence` — permitted matching chunks and source context.
- `POST /api/v1/search/{search_id}/feedback` — optional relevance or result feedback.

### 10.4 User history and preferences

- `GET /api/v1/me/preferences` and `PUT /api/v1/me/preferences`.
- `GET /api/v1/me/history` — paginated history with redaction policy.
- `DELETE /api/v1/me/history` — clear history.
- `POST /api/v1/me/personalization/disable` — disable personalization.

### 10.5 Evaluation and administration

- `GET /api/v1/admin/ingestion/failures` — review extraction/index failures.
- `POST /api/v1/admin/evaluation/runs` — run an offline evaluation configuration.
- `GET /api/v1/admin/evaluation/runs/{run_id}` — retrieve metrics and configuration.

All endpoints require request validation, consistent error responses, pagination limits, authorization checks, and explicit rate/size limits where relevant.

## 11. Testing and Evaluation

### 11.1 Test layers

- **Unit tests:** path validation, parsers, chunking, query normalization, RRF, score aggregation, personalization caps, and workflow transitions.
- **Integration tests:** PostgreSQL full-text and pgvector queries, migrations, ingestion-to-search flow, and transaction behavior.
- **API tests:** request validation, authorization, error responses, pagination, and response schemas.
- **End-to-end tests:** ingest approved files, search, inspect evidence, open a permitted file, and clear history.
- **Evaluation tests:** fixed dataset, fixed model/configuration, repeatable metric generation.
- **Failure tests:** corrupt files, unsupported types, inaccessible paths, model failures, empty results, and timeout/retry behavior.

### 11.2 Metrics

- **Precision@K:** fraction of the top K results judged relevant.
- **Recall@K:** fraction of all known relevant documents retrieved in the top K.
- **MRR:** reciprocal rank of the first relevant result, averaged across queries.
- **NDCG@K:** graded relevance quality with higher weight for higher ranks.
- **Search latency:** end-to-end and per-stage latency, including p50 and p95.
- **Agent success rate:** percentage of queries meeting the defined result-sufficiency criterion within the retry/time budget.
- **Failure rate:** ingestion and search failures by category.

Report confidence limitations: a small manually labeled dataset cannot establish universal performance.

### 11.3 Baseline experiment

Use the versioned 300–500-file corpus manifest, 40-query set, and relevance labels from Section 8.6. Before each run, verify file checksums and recreate or validate the database indexes. Run each retrieval configuration in a clean evaluation run with the same query order, top-K values, chunking settings, model versions, preprocessing, database indexes, hardware profile, and cache policy. Use fixed random seeds where supported and record the software revision, configuration, start/end timestamps, and environment details.

For each configuration, export per-query ranked file IDs and graded labels before calculating aggregate Precision@K, Recall@K, MRR, and NDCG@K. Report p50/p95 end-to-end and per-stage latency over the same query set, plus agent success and retry counts for adaptive runs. Repeat each configuration at least three times for latency measurements, while using one designated quality run for the primary comparison. Compare quality and latency, then inspect failure examples qualitatively. Personalization must be evaluated in a separate run with a defined interaction-history fixture so it cannot hide degradation in base relevance.

## 12. Development Roadmap

### Phase 0 — Project decisions and reproducibility

- **Objective:** Confirm scope, supported formats, privacy posture, corpus source, and evaluation protocol.
- **Tasks:** Establish coding conventions; choose Python and Node versions; define API versioning; define the evaluation dataset format; identify permitted documents.
- **Dependencies:** None.
- **Expected output:** Approved scope, architecture baseline, dataset policy, and acceptance criteria.
- **Testing criteria:** Review checklist confirms every core feature has an observable acceptance criterion.
- **Completion criteria:** No unresolved decision changes the core architecture.

### Phase 1 — Repository and domain foundation

- **Objective:** Create the project structure and domain contracts.
- **Tasks:** Initialize frontend/backend project manifests; define configuration handling; create domain types; establish linting, formatting, and pytest structure; define error and logging conventions.
- **Dependencies:** Phase 0.
- **Expected output:** Buildable empty shells and documented module boundaries.
- **Testing criteria:** Static checks pass; health endpoint and frontend shell can be exercised.
- **Completion criteria:** Local development workflow is reproducible without application-specific shortcuts.

### Phase 2 — Database and file catalog

- **Objective:** Persist users, files, chunks, embeddings metadata, and histories.
- **Tasks:** Implement SQLAlchemy models and Alembic migrations; add indexes and constraints; add repository interfaces; implement path and checksum rules.
- **Dependencies:** Phase 1.
- **Expected output:** Migratable PostgreSQL schema and catalog operations.
- **Testing criteria:** Migration tests, constraint tests, duplicate detection, and path-security tests pass.
- **Completion criteria:** A file can be registered and its lifecycle status can be queried.

### Phase 3 — Ingestion and extraction

- **Objective:** Convert supported files into stable searchable chunks.
- **Tasks:** Implement format adapters; normalize metadata; handle unsupported/corrupt files; chunk text; add incremental re-indexing and deletion behavior.
- **Dependencies:** Phase 2.
- **Expected output:** Ingestion pipeline with status reporting.
- **Testing criteria:** Fixture tests for every supported format, malformed input, idempotency, and checksum changes.
- **Completion criteria:** Approved fixture files are extracted and chunked with no silent failures.

### Phase 4 — Embeddings and baseline retrieval

- **Objective:** Make indexed chunks searchable.
- **Tasks:** Generate and persist embeddings; add pgvector indexes/configuration; implement keyword and semantic retrieval; aggregate chunks to files.
- **Dependencies:** Phase 3.
- **Expected output:** Reproducible keyword and semantic search APIs.
- **Testing criteria:** Retrieval integration tests, empty-result tests, filter tests, and model metadata checks.
- **Completion criteria:** Baseline queries return expected evidence from the fixture corpus.

### Phase 5 — Hybrid retrieval and reranking

- **Objective:** Improve result quality and establish comparable strategies.
- **Tasks:** Implement RRF; define duplicate and tie handling; add optional cross-encoder reranking; expose strategy selection for experiments.
- **Dependencies:** Phase 4.
- **Expected output:** Keyword, semantic, hybrid, and reranked modes with consistent response schemas.
- **Testing criteria:** Mathematical unit tests for RRF, candidate-limit tests, latency measurements, and regression fixtures.
- **Completion criteria:** Strategy outputs are reproducible and explainable.

### Phase 6 — Bounded agentic workflow

- **Objective:** Add explicit adaptive orchestration without unnecessary autonomous agents.
- **Tasks:** Implement query understanding, tool registry, strategy selection, sufficiency evaluator, retry budget, trace recording, and safe fallback behavior.
- **Dependencies:** Phase 5.
- **Expected output:** Agentic search workflow with trace identifiers and termination reasons.
- **Testing criteria:** State-transition tests, retry-budget tests, tool-failure tests, timeout tests, and trace-redaction tests.
- **Completion criteria:** The workflow demonstrably selects tools and adapts on weak results without bypassing deterministic safeguards.

### Phase 7 — Personalization and user experience

- **Objective:** Provide a usable search UI and conservative personalization.
- **Tasks:** Build search, filters, result evidence, ingestion status, feedback, preferences, and history controls; implement bounded history/access signals.
- **Dependencies:** Phase 6 and a usable API contract.
- **Expected output:** End-to-end user workflow.
- **Testing criteria:** API/UI integration tests, access-control tests, opt-out and deletion tests, and usability review.
- **Completion criteria:** A user can ingest, search, inspect evidence, and control personalization.

### Phase 8 — Evaluation, hardening, and demonstration

- **Objective:** Measure the system and prepare the capstone demonstration.
- **Tasks:** Label the evaluation dataset; run baselines and adaptive variants; measure quality/latency; fix reproducible defects; document limitations and setup.
- **Dependencies:** Phases 1–7.
- **Expected output:** Evaluation report, reproducible run instructions, test evidence, and demonstration scenario.
- **Testing criteria:** Full automated suite passes; metrics and configurations are archived; security/privacy checklist passes.
- **Completion criteria:** Core requirements are demonstrated and all excluded features remain out of scope unless explicitly approved.

## 13. Risks and Limitations

### Technical risks

- pgvector indexing and query tuning may be more complex than expected.
- Local model inference may exceed acceptable latency or memory.
- Cross-encoder reranking can improve quality while making interactive search slow.
- Format extraction may lose tables, layout, or context.
- Chunk size and overlap choices can materially affect results.
- A modular monolith can become tightly coupled if module boundaries are not enforced.

### Dataset and evaluation risks

- A small manually labeled corpus may produce unstable or non-generalizable metrics.
- Relevance judgments can reflect one evaluator’s assumptions.
- Synthetic documents may overstate performance compared with messy real files.
- Access-history data may be sparse, biased, or unavailable for cold-start users.

### Model limitations

- `all-MiniLM-L6-v2` is a general baseline, not a domain-optimal model.
- Embeddings can miss exact identifiers, negation, tables, and highly specialized terms.
- Cross-encoders add compute cost and can inherit training-data biases.
- Query expansion can introduce incorrect terms or drift from the user’s intent.
- An LLM can hallucinate explanations unless explanations are grounded in retrieved evidence.

### Privacy and security risks

- Extracted text, embeddings, queries, and access history are sensitive.
- Path traversal or weak access checks could expose local files.
- Logs and traces could accidentally retain document content.
- A future external LLM integration could transfer confidential content.
- Deleting a file from the catalog may not automatically remove every backup, cache, or history record.

### Implementation challenges and mitigations

- Start with a small, explicit format set and fixture corpus.
- Keep deterministic retrieval as the reliable fallback.
- Bound candidate counts, retries, tokens, and execution time.
- Version models, chunking settings, and evaluation datasets.
- Add security tests before enabling file opening or multi-user access.
- Defer OCR, cloud connectors, and distributed services until a measured requirement exists.

## 14. Definition of a Successful Initial Capstone

The initial project is successful when a user can index an approved collection, search it with natural language, receive evidence-backed results from keyword/semantic/hybrid retrieval, observe a bounded adaptive workflow trace, and see measurable evaluation results against a labeled dataset. The implementation should explain where agentic behavior exists, where deterministic retrieval is used, and which limitations prevent production-grade claims.
