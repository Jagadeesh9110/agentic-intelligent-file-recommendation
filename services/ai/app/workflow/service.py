from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.db.models.agent_execution_trace import AgentExecutionTrace
from app.reranking.service import RerankedResult, RerankerService
from app.retrieval.hybrid import HybridRetriever, RetrievalResult

ALLOWED_STRATEGIES = {"full_text", "semantic", "hybrid"}


@dataclass(frozen=True, slots=True)
class Recommendation:
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


@dataclass(frozen=True, slots=True)
class WorkflowResult:
    trace_id: UUID
    query: str
    status: str
    strategy: str
    recommendations: tuple[Recommendation, ...]
    summary: str
    tool_calls: int
    refinement_attempted: bool


class WorkflowLimitError(RuntimeError):
    """Raised when bounded workflow execution exceeds its limits."""


class AgentWorkflow:
    """A deterministic, single-agent search workflow with bounded execution."""

    def __init__(
        self,
        retriever: HybridRetriever,
        reranker: RerankerService,
        *,
        max_tool_calls: int = settings.workflow_max_tool_calls,
        timeout_seconds: float = settings.workflow_timeout_seconds,
        max_refinements: int = settings.workflow_max_refinements,
    ) -> None:
        if max_tool_calls <= 0 or timeout_seconds <= 0:
            raise ValueError("Workflow limits must be greater than zero.")
        if not 0 <= max_refinements <= 1:
            raise ValueError("Workflow refinements must be between zero and one.")
        self.retriever = retriever
        self.reranker = reranker
        self.max_tool_calls = max_tool_calls
        self.timeout_seconds = timeout_seconds
        self.max_refinements = max_refinements

    def run(
        self,
        session: Session,
        query: str,
        *,
        limit: int = 10,
        strategy: str = "hybrid",
        rrf_constant: int | None = None,
    ) -> WorkflowResult:
        normalized_query = " ".join(query.split())
        if not normalized_query:
            raise ValueError("Search query cannot be empty.")
        if strategy not in ALLOWED_STRATEGIES:
            raise ValueError(f"Unsupported retrieval strategy: {strategy}")
        if limit <= 0:
            raise ValueError("Result limit must be greater than zero.")

        started = time.monotonic()
        trace_id = uuid4()
        tool_calls = 0
        refinement_attempted = False
        attempts: list[dict[str, Any]] = []
        try:
            results = self._retrieve(
                session,
                normalized_query,
                strategy,
                limit,
                rrf_constant,
                attempts,
                started,
                tool_calls,
            )
            tool_calls = self._tool_count(strategy)
            reranked = self.reranker.rerank(normalized_query, results)
            tool_calls += 1
            self._check_budget(started, tool_calls)

            if not reranked and self.max_refinements:
                refinement_attempted = True
                refined_query = normalized_query
                results = self._retrieve(
                    session,
                    refined_query,
                    strategy,
                    limit,
                    rrf_constant,
                    attempts,
                    started,
                    tool_calls,
                )
                tool_calls += self._tool_count(strategy)
                reranked = self.reranker.rerank(refined_query, results)
                tool_calls += 1
                self._check_budget(started, tool_calls)

            recommendations = tuple(_recommendation(item) for item in reranked)
            result = WorkflowResult(
                trace_id=trace_id,
                query=normalized_query,
                status="completed",
                strategy=strategy,
                recommendations=recommendations,
                summary=(
                    f"Found {len(recommendations)} recommendation(s)."
                    if recommendations
                    else "No relevant files were found."
                ),
                tool_calls=tool_calls,
                refinement_attempted=refinement_attempted,
            )
            self._persist_trace(session, result, attempts, None, started, rrf_constant)
            return result
        except Exception as error:
            self._persist_trace(
                session,
                WorkflowResult(
                    trace_id=trace_id,
                    query=normalized_query,
                    status="failed",
                    strategy=strategy,
                    recommendations=(),
                    summary="Search execution failed.",
                    tool_calls=tool_calls,
                    refinement_attempted=refinement_attempted,
                ),
                attempts,
                str(error),
                started,
                rrf_constant,
            )
            raise

    def _retrieve(
        self,
        session: Session,
        query: str,
        strategy: str,
        limit: int,
        rrf_constant: int | None,
        attempts: list[dict[str, Any]],
        started: float,
        current_calls: int,
    ) -> tuple[RetrievalResult, ...]:
        needed = self._tool_count(strategy)
        self._check_budget(started, current_calls + needed)
        if strategy == "full_text":
            results = self.retriever.full_text(session, query, limit=limit)
        elif strategy == "semantic":
            results = self.retriever.semantic(session, query, limit=limit)
        else:
            results = self.retriever.hybrid(
                session, query, limit=limit, rrf_constant=rrf_constant
            )
        attempts.append({"strategy": strategy, "result_count": len(results)})
        if rrf_constant is not None and strategy == "hybrid":
            attempts[-1]["rrf_constant"] = rrf_constant
        return results

    def _tool_count(self, strategy: str) -> int:
        return 2 if strategy == "hybrid" else 1

    def _check_budget(self, started: float, calls: int) -> None:
        if calls > self.max_tool_calls:
            raise WorkflowLimitError("Maximum workflow tool-call count exceeded.")
        if time.monotonic() - started > self.timeout_seconds:
            raise WorkflowLimitError("Workflow execution timed out.")

    @staticmethod
    def _persist_trace(
        session: Session,
        result: WorkflowResult,
        attempts: list[dict[str, Any]],
        error: str | None,
        started: float,
        rrf_constant: int | None,
    ) -> None:
        trace = AgentExecutionTrace(
            id=result.trace_id,
            normalized_query=result.query,
            selected_strategy=result.strategy,
            attempts=attempts,
            tool_decisions=[
                {"tool": source, "allowed": True}
                for source in ("full_text_search", "semantic_search")
            ],
            result_counts={"recommendations": len(result.recommendations)},
            timings={"duration_ms": round((time.monotonic() - started) * 1000, 2)},
            model_metadata={"rrf_constant": rrf_constant} if rrf_constant else None,
            termination_reason=error or result.summary,
        )
        session.add(trace)
        session.commit()


def _recommendation(item: RerankedResult) -> Recommendation:
    result = item.result
    return Recommendation(
        file_id=result.file_id,
        chunk_id=result.chunk_id,
        text=result.text,
        chunk_ordinal=result.chunk_ordinal,
        page_number=result.page_number,
        sheet_name=result.sheet_name,
        section_name=result.section_name,
        retrieval_score=result.score,
        fused_score=result.fused_score,
        reranking_score=item.reranking_score,
        retrieval_sources=result.retrieval_sources,
        explanation="Matched the query through " + ", ".join(result.retrieval_sources),
    )
