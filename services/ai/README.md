# AI service

Minimal FastAPI service for the file recommendation system. Database integration,
document processing, embeddings, retrieval, and agentic workflows will be added
in later phases.

## Setup

From `services/ai`, create and activate the local virtual environment:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and adjust local settings as needed.

## Run

```powershell
python -m uvicorn app.main:app --reload
```

The health endpoint is available at `http://127.0.0.1:8000/health`.

## Checks

```powershell
ruff check .
ruff format --check .
pytest
```
