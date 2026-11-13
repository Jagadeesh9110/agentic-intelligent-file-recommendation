from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class RetrievalConfig(BaseModel):
    strategy: Literal["full_text", "semantic", "hybrid"] = "hybrid"
    rrf_constant: int | None = Field(default=None, ge=1, le=1000)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=10, ge=1, le=50)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)


class RecommendationResponse(BaseModel):
    file_id: UUID
    chunk_id: UUID
    text: str
    chunk_ordinal: int
    page_number: int | None
    sheet_name: str | None
    section_name: str | None
    retrieval_score: float
    fused_score: float | None
    reranking_score: float
    retrieval_sources: tuple[str, ...]
    explanation: str


class SearchResponse(BaseModel):
    trace_id: UUID
    query: str
    execution_status: str
    strategy: str
    recommendations: tuple[RecommendationResponse, ...]
    execution_summary: str
    tool_calls: int
    refinement_attempted: bool
