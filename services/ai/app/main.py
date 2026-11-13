from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config.settings import settings
from app.embeddings.service import EmbeddingService
from app.reranking.service import RerankerService
from app.retrieval.hybrid import HybridRetriever
from app.workflow.service import AgentWorkflow, WorkflowLimitError

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)
workflow = AgentWorkflow(
    HybridRetriever(EmbeddingService()),
    RerankerService(),
)
app.include_router(router)


@app.exception_handler(ValueError)
def handle_validation_error(_: Request, error: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(error)})


@app.exception_handler(WorkflowLimitError)
def handle_workflow_limit(_: Request, error: WorkflowLimitError) -> JSONResponse:
    return JSONResponse(status_code=504, content={"detail": str(error)})


@app.exception_handler(RuntimeError)
def handle_runtime_error(_: Request, error: RuntimeError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(error)})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
