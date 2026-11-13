from dataclasses import dataclass

from app.documents.models import DocumentChunkData, ExtractedDocument
from app.documents.normalization import normalize_text


@dataclass(frozen=True, slots=True)
class ChunkConfig:
    max_characters: int = 1200
    overlap_characters: int = 120

    def __post_init__(self) -> None:
        if self.max_characters <= 0:
            raise ValueError("max_characters must be greater than zero.")
        if self.overlap_characters < 0:
            raise ValueError("overlap_characters cannot be negative.")
        if self.overlap_characters >= self.max_characters:
            raise ValueError("overlap_characters must be smaller than max_characters.")


def chunk_document(
    document: ExtractedDocument,
    config: ChunkConfig | None = None,
) -> tuple[DocumentChunkData, ...]:
    """Create deterministic, metadata-preserving chunks for an extracted document."""
    chunk_config = config or ChunkConfig()
    chunks: list[DocumentChunkData] = []
    for segment in document.segments:
        normalized = normalize_text(segment.text)
        if not normalized:
            continue
        for text in _chunk_text(normalized, chunk_config):
            chunks.append(
                DocumentChunkData(
                    chunk_ordinal=len(chunks),
                    extracted_text=text,
                    normalized_search_text=text,
                    page_number=segment.page_number,
                    sheet_name=segment.sheet_name,
                    section_name=segment.section_name,
                    character_count=len(text),
                )
            )
    return tuple(chunks)


def _chunk_text(text: str, config: ChunkConfig) -> tuple[str, ...]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        limit = min(start + config.max_characters, len(text))
        end = limit
        if limit < len(text):
            paragraph_boundary = text.rfind("\n\n", start + 1, limit + 2)
            if start < paragraph_boundary <= limit:
                end = paragraph_boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        next_start = max(end - config.overlap_characters, start + 1)
        start = next_start
    return tuple(chunks)
