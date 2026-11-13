from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExtractedSegment:
    text: str
    page_number: int | None = None
    sheet_name: str | None = None
    section_name: str | None = None


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    filename: str
    file_type: str
    segments: tuple[ExtractedSegment, ...]


@dataclass(frozen=True, slots=True)
class DocumentChunkData:
    chunk_ordinal: int
    extracted_text: str
    normalized_search_text: str
    page_number: int | None = None
    sheet_name: str | None = None
    section_name: str | None = None
    token_count: int | None = None
    character_count: int = 0
