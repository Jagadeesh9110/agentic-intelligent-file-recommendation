from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol

from sentence_transformers import CrossEncoder

from app.config.settings import settings
from app.retrieval.hybrid import RetrievalResult


class _CrossEncoderModel(Protocol):
    def predict(self, sentences: list[tuple[str, str]], **kwargs: Any) -> Any: ...


@lru_cache(maxsize=4)
def _load_model(model_name: str, device: str) -> CrossEncoder:
    return CrossEncoder(model_name, device=device)


@dataclass(frozen=True, slots=True)
class RerankedResult:
    result: RetrievalResult
    reranking_score: float


class RerankerService:
    def __init__(
        self,
        *,
        model_name: str = settings.reranker_model_name,
        batch_size: int = settings.reranker_batch_size,
        candidate_limit: int = settings.reranker_candidate_limit,
        device: str = settings.embedding_device,
        model: _CrossEncoderModel | None = None,
    ) -> None:
        if batch_size <= 0 or candidate_limit <= 0:
            raise ValueError("Reranker limits must be greater than zero.")
        if device.lower() != "cpu":
            raise ValueError("Reranking must use the CPU device.")
        self.model_name = model_name
        self.batch_size = batch_size
        self.candidate_limit = candidate_limit
        self.device = device
        self._model = model

    @property
    def model(self) -> _CrossEncoderModel:
        if self._model is None:
            self._model = _load_model(self.model_name, self.device)
        return self._model

    def rerank(
        self, query: str, results: list[RetrievalResult] | tuple[RetrievalResult, ...]
    ) -> tuple[RerankedResult, ...]:
        if not query.strip() or not results:
            return ()
        candidates = tuple(results[: self.candidate_limit])
        pairs = [(query.strip(), result.text) for result in candidates]
        try:
            scores = self.model.predict(
                pairs,
                batch_size=self.batch_size,
                show_progress_bar=False,
            )
            if len(scores) != len(candidates):
                raise ValueError("Reranker returned a different number of scores.")
            ranked = tuple(
                RerankedResult(result=result, reranking_score=float(score))
                for result, score in zip(candidates, scores, strict=True)
            )
            return tuple(
                sorted(
                    ranked,
                    key=lambda item: (-item.reranking_score, str(item.result.chunk_id)),
                )
            )
        except ValueError:
            raise
        except Exception as error:
            raise RuntimeError(f"Cross-encoder reranking failed: {error}") from error
