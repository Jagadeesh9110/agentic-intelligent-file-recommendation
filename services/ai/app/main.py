from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.ingestion_routes import router as ingestion_router
from app.api.routes import router
from app.config.settings import settings
from app.embeddings.service import EmbeddingService
from app.reranking.service import RerankerService
from app.retrieval.hybrid import HybridRetriever
from app.workflow.service import AgentWorkflow, WorkflowLimitError

app = FastAPI(title=settings.app_name, version="0.1.0")

embedding_service = EmbeddingService()

workflow = AgentWorkflow(
    HybridRetriever(embedding_service),
    RerankerService(),
)

app.include_router(router)
app.include_router(ingestion_router)


@app.exception_handler(ValueError)
def handle_value_error(request: Request, error: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(error)},
    )


@app.exception_handler(WorkflowLimitError)
def handle_workflow_limit_error(request: Request, error: WorkflowLimitError):
    return JSONResponse(
        status_code=422,
        content={"detail": str(error)},
    )


@app.exception_handler(RuntimeError)
def handle_runtime_error(request: Request, error: RuntimeError):
    return JSONResponse(
        status_code=500,
        content={"detail": str(error)},
    )


@app.get("/health")
def health():
    return {"status": "ok"}
