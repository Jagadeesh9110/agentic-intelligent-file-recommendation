from __future__ import annotations

import secrets
from collections.abc import Generator

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import RecommendationResponse, SearchRequest, SearchResponse
from app.config.settings import settings
from app.db.base import session_factory
from app.workflow.service import AgentWorkflow

router = APIRouter(prefix="/api/v1", tags=["search"])


def verify_ai_service_key(
    api_key: str | None = Header(default=None, alias="X-AI-Service-Key"),
) -> None:
    configured_key = settings.ai_service_api_key

    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service authentication is not configured.",
        )

    if not api_key or not secrets.compare_digest(api_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing AI service API key.",
        )


def get_db_session() -> Generator[Session]:
    with session_factory() as session:
        yield session


def get_workflow() -> AgentWorkflow:
    from app.main import workflow

    return workflow


@router.post(
    "/search",
    response_model=SearchResponse,
    dependencies=[Depends(verify_ai_service_key)],
)
def search(
    request: SearchRequest,
    session: Session = Depends(get_db_session),  # noqa: B008
    current_workflow: AgentWorkflow = Depends(get_workflow),  # noqa: B008
) -> SearchResponse:
    result = current_workflow.run(
        session,
        request.query,
        limit=request.limit,
        strategy=request.retrieval.strategy,
        rrf_constant=request.retrieval.rrf_constant,
    )

    return SearchResponse(
        trace_id=result.trace_id,
        query=result.query,
        execution_status=result.status,
        strategy=result.strategy,
        recommendations=tuple(
            RecommendationResponse.model_validate(
                recommendation,
                from_attributes=True,
            )
            for recommendation in result.recommendations
        ),
        execution_summary=result.summary,
        tool_calls=result.tool_calls,
        refinement_attempted=result.refinement_attempted,
    )
