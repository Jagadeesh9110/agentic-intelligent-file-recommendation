from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.routes import get_workflow
from app.main import app
from app.workflow.service import Recommendation, WorkflowResult


class _Workflow:
    def run(self, session, query, *, limit, strategy, rrf_constant):
        return WorkflowResult(
            trace_id=uuid4(),
            query=query,
            status="completed",
            strategy=strategy,
            recommendations=(
                Recommendation(
                    file_id=uuid4(),
                    chunk_id=uuid4(),
                    text="snippet",
                    chunk_ordinal=0,
                    page_number=1,
                    sheet_name=None,
                    section_name=None,
                    retrieval_score=0.5,
                    fused_score=0.03,
                    reranking_score=0.9,
                    retrieval_sources=("full_text", "semantic"),
                    explanation="Matched through full_text, semantic",
                ),
            ),
            summary="Found 1 recommendation(s).",
            tool_calls=3,
            refinement_attempted=False,
        )


def test_search_api_validates_requests_and_returns_contract() -> None:
    app.dependency_overrides[get_workflow] = lambda: _Workflow()
    try:
        client = TestClient(app)
        response = client.post("/api/v1/search", json={"query": "architecture"})
        assert response.status_code == 200
        body = response.json()
        assert body["execution_status"] == "completed"
        assert body["recommendations"][0]["reranking_score"] == 0.9
    finally:
        app.dependency_overrides.clear()


def test_search_api_rejects_empty_query() -> None:
    response = TestClient(app).post("/api/v1/search", json={"query": ""})
    assert response.status_code == 422
