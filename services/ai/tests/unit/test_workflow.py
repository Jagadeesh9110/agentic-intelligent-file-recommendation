from uuid import uuid4

import pytest

from app.reranking.service import RerankedResult
from app.retrieval.hybrid import RetrievalResult
from app.workflow.service import AgentWorkflow, WorkflowLimitError


def _retrieval_result() -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid4(),
        file_id=uuid4(),
        text="matching content",
        chunk_ordinal=1,
        page_number=2,
        sheet_name=None,
        section_name="Overview",
        score=0.8,
        retrieval_sources=("full_text", "semantic"),
        fused_score=0.03,
    )


class _Session:
    def __init__(self) -> None:
        self.added = []
        self.commits = 0

    def add(self, value) -> None:
        self.added.append(value)

    def commit(self) -> None:
        self.commits += 1


class _Retriever:
    def hybrid(self, session, query, *, limit, rrf_constant=None):
        return (_retrieval_result(),)

    def full_text(self, session, query, *, limit):
        return (_retrieval_result(),)

    def semantic(self, session, query, *, limit):
        return (_retrieval_result(),)


class _Reranker:
    def rerank(self, query, results):
        return (RerankedResult(results[0], 0.95),) if results else ()


def test_workflow_runs_bounded_stages_and_persists_trace() -> None:
    session = _Session()
    result = AgentWorkflow(_Retriever(), _Reranker()).run(
        session, "  matching   content ", limit=3
    )

    assert result.status == "completed"
    assert result.query == "matching content"
    assert result.tool_calls == 3
    assert result.recommendations[0].reranking_score == 0.95
    assert result.recommendations[0].page_number == 2
    assert len(session.added) == 1
    assert session.commits == 1


def test_workflow_rejects_unknown_strategy_and_enforces_call_limit() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        AgentWorkflow(_Retriever(), _Reranker()).run(
            _Session(), "query", strategy="unknown"
        )
    with pytest.raises(WorkflowLimitError):
        AgentWorkflow(_Retriever(), _Reranker(), max_tool_calls=1).run(
            _Session(), "query"
        )
