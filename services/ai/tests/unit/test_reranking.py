from uuid import uuid4

from app.reranking.service import RerankerService
from app.retrieval.hybrid import RetrievalResult


def _result(text: str) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid4(),
        file_id=uuid4(),
        text=text,
        chunk_ordinal=0,
        page_number=None,
        sheet_name=None,
        section_name=None,
        score=0.5,
        retrieval_sources=("semantic",),
    )


class _Model:
    def predict(self, sentences, **kwargs):
        assert kwargs["batch_size"] == 2
        return [0.2, 0.9][: len(sentences)]


def test_reranker_sorts_by_cross_encoder_score_and_preserves_metadata() -> None:
    first = _result("first")
    second = _result("second")

    reranked = RerankerService(
        model_name="test",
        batch_size=2,
        candidate_limit=10,
        model=_Model(),
    ).rerank("query", [first, second])

    assert [item.result.text for item in reranked] == ["second", "first"]
    assert reranked[0].reranking_score == 0.9
    assert reranked[0].result.retrieval_sources == ("semantic",)


def test_reranker_applies_candidate_limit_and_empty_input() -> None:
    model = _Model()
    service = RerankerService(model=model, batch_size=2, candidate_limit=1)
    assert service.rerank("", [_result("empty")]) == ()
    result = service.rerank("query", [_result("one"), _result("two")])
    assert len(result) == 1
