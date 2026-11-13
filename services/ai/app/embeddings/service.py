from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

from sentence_transformers import SentenceTransformer

from app.config.settings import settings
from app.db.models.document_chunk import DocumentChunk

EMBEDDING_DIMENSION = 384
MODEL_VERSION = "1"


class EmbeddingGenerationError(ValueError):
    """Raised when an embedding cannot be generated or validated."""


class _EmbeddingModel(Protocol):
    def encode(self, sentences: list[str], **kwargs: Any) -> Any: ...


@dataclass(frozen=True, slots=True)
class GeneratedEmbedding:
    chunk: DocumentChunk
    vector: tuple[float, ...]


@lru_cache(maxsize=8)
def _load_model(
    model_name: str,
    cache_dir: str | None,
    device: str,
) -> SentenceTransformer:
    kwargs: dict[str, Any] = {"device": device}
    if cache_dir:
        kwargs["cache_folder"] = str(Path(cache_dir))
    return SentenceTransformer(model_name, **kwargs)


class EmbeddingService:
    """Generate validated local embeddings for persisted document chunks."""

    def __init__(
        self,
        *,
        model_name: str = settings.embedding_model_name,
        cache_dir: str | None = settings.model_cache_dir,
        batch_size: int = settings.embedding_batch_size,
        device: str = settings.embedding_device,
        model: _EmbeddingModel | None = None,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("Embedding batch size must be greater than zero.")
        if device.lower() != "cpu":
            raise ValueError("Embedding generation must use the CPU device.")
        self.model_name = model_name
        self.model_version = MODEL_VERSION
        self.batch_size = batch_size
        self.device = device
        self._cache_dir = cache_dir
        self._model = model

    @property
    def model(self) -> _EmbeddingModel:
        if self._model is None:
            self._model = _load_model(self.model_name, self._cache_dir, self.device)
        return self._model

    def generate(
        self, chunks: list[DocumentChunk] | tuple[DocumentChunk, ...]
    ) -> tuple[GeneratedEmbedding, ...]:
        if not chunks:
            return ()
        texts: list[str] = []
        for chunk in chunks:
            text = chunk.extracted_text.strip()
            if not text:
                raise EmbeddingGenerationError(
                    f"Chunk {chunk.id} has no text to embed."
                )
            texts.append(text)

        vectors = self._encode_texts(texts)
        return tuple(
            GeneratedEmbedding(chunk=chunk, vector=vector)
            for chunk, vector in zip(chunks, vectors, strict=True)
        )

    def generate_query_embedding(self, query: str) -> tuple[float, ...]:
        """Generate one validated embedding for a search query."""
        if not query.strip():
            raise EmbeddingGenerationError("Search query cannot be empty.")
        return self._encode_texts([query.strip()])[0]

    def _encode_texts(self, texts: list[str]) -> tuple[tuple[float, ...], ...]:
        try:
            vectors = self.model.encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=False,
            )
            if len(vectors) != len(texts):
                raise EmbeddingGenerationError(
                    "Embedding model returned a different number of vectors "
                    "than input texts."
                )
            return tuple(_validate_vector(vector) for vector in vectors)
        except EmbeddingGenerationError:
            raise
        except Exception as error:
            raise EmbeddingGenerationError(
                f"Embedding generation failed for {len(texts)} texts: {error}"
            ) from error


def _validate_vector(vector: Any) -> tuple[float, ...]:
    try:
        values = tuple(float(value) for value in vector)
    except (TypeError, ValueError) as error:
        raise EmbeddingGenerationError(
            "Embedding model returned non-numeric values."
        ) from error
    if len(values) != EMBEDDING_DIMENSION:
        raise EmbeddingGenerationError(
            f"Embedding vector must contain exactly {EMBEDDING_DIMENSION} values; "
            f"received {len(values)}."
        )
    if not all(math.isfinite(value) for value in values):
        raise EmbeddingGenerationError("Embedding vector contains non-finite values.")
    return values
