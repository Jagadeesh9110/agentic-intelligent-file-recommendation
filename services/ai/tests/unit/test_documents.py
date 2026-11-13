from io import BytesIO

import fitz
import openpyxl
import pytest
from docx import Document

from app.documents.chunking import ChunkConfig, chunk_document
from app.documents.exceptions import (
    DocumentExtractionError,
    EmptyDocumentError,
    UnsupportedDocumentError,
)
from app.documents.extraction import extract_document
from app.documents.models import ExtractedDocument, ExtractedSegment
from app.documents.normalization import normalize_text


def _pdf_bytes(text: str = "PDF heading\nPDF body") -> bytes:
    document = fitz.open()
    page = document.new_page()
    if text:
        page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content


def _docx_bytes() -> bytes:
    document = Document()
    document.add_heading("Project heading", level=1)
    document.add_paragraph("Unicode text: café — résumé")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Name"
    table.cell(0, 1).text = "Value"
    table.cell(1, 0).text = "Mode"
    table.cell(1, 1).text = "Test"
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def _xlsx_bytes() -> bytes:
    workbook = openpyxl.Workbook()
    first = workbook.active
    first.title = "Summary"
    first.append(["Name", "Value"])
    first.append(["Count", 3])
    second = workbook.create_sheet("Details")
    second.append(["Key", "Description"])
    second.append(["A", "Unicode café"])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_extracts_pdf_text_and_page_numbers() -> None:
    document = extract_document(_pdf_bytes(), "report.pdf")

    assert document.file_type == "pdf"
    assert document.segments[0].page_number == 1
    assert "PDF heading" in document.segments[0].text


def test_reports_pdf_without_extractable_text() -> None:
    with pytest.raises(EmptyDocumentError, match="OCR is not supported"):
        extract_document(_pdf_bytes(""), "scanned.pdf")


def test_extracts_docx_paragraphs_tables_and_heading_context() -> None:
    document = extract_document(_docx_bytes(), "report.docx")

    texts = [segment.text for segment in document.segments]
    assert any("Unicode text" in text for text in texts)
    assert any("Name | Value" in text for text in texts)
    assert document.segments[0].section_name == "Project heading"


def test_extracts_xlsx_rows_from_multiple_sheets() -> None:
    document = extract_document(_xlsx_bytes(), "workbook.xlsx")

    assert {segment.sheet_name for segment in document.segments} == {
        "Summary",
        "Details",
    }
    assert any("A2" in segment.text for segment in document.segments)
    assert any("Count" in segment.text for segment in document.segments)


def test_extracts_csv_headers_and_rows_with_column_context() -> None:
    content = b"name,value\nCount,3\nMode,Test\n"

    document = extract_document(content, "values.csv")

    assert "name: Count" in document.segments[0].text
    assert "value: 3" in document.segments[0].text
    assert document.segments[0].section_name == "CSV row 2"


def test_extracts_utf8_txt() -> None:
    document = extract_document("Hello\n\ncafé".encode(), "notes.txt")

    assert document.segments[0].text == "Hello\n\ncafé"


def test_rejects_unsupported_and_corrupted_documents() -> None:
    with pytest.raises(UnsupportedDocumentError, match="Unsupported"):
        extract_document(b"content", "notes.md")
    with pytest.raises(DocumentExtractionError, match="Could not read DOCX"):
        extract_document(b"not a docx", "broken.docx")


def test_reports_empty_documents() -> None:
    with pytest.raises(EmptyDocumentError):
        extract_document(b" \r\n\t ", "empty.txt")


def test_normalization_preserves_paragraphs_and_unicode() -> None:
    text = " café \r\n\r\n  important\tvalue \n\n\n next "

    assert normalize_text(text) == "café\n\nimportant value\n\nnext"


def test_chunks_respect_size_overlap_and_metadata() -> None:
    source = ExtractedDocument(
        filename="notes.txt",
        file_type="txt",
        segments=(
            ExtractedSegment(
                text="abcdefghij" * 8,
                page_number=4,
                section_name="Section A",
            ),
        ),
    )

    chunks = chunk_document(
        source, ChunkConfig(max_characters=20, overlap_characters=5)
    )

    assert len(chunks) > 1
    assert all(0 < chunk.character_count <= 20 for chunk in chunks)
    assert chunks[1].extracted_text.startswith(chunks[0].extracted_text[-5:])
    assert all(chunk.page_number == 4 for chunk in chunks)
    assert all(chunk.section_name == "Section A" for chunk in chunks)
    assert [chunk.chunk_ordinal for chunk in chunks] == list(range(len(chunks)))


def test_chunks_preserve_paragraph_boundaries_when_possible() -> None:
    source = ExtractedDocument(
        filename="notes.txt",
        file_type="txt",
        segments=(ExtractedSegment(text="first\n\nsecond\n\nthird"),),
    )

    chunks = chunk_document(
        source, ChunkConfig(max_characters=13, overlap_characters=0)
    )

    assert [chunk.extracted_text for chunk in chunks] == [
        "first\n\nsecond",
        "third",
    ]


def test_chunking_is_deterministic_and_splits_oversized_paragraphs() -> None:
    source = ExtractedDocument(
        filename="notes.txt",
        file_type="txt",
        segments=(ExtractedSegment(text="x" * 51),),
    )
    config = ChunkConfig(max_characters=10, overlap_characters=2)

    first = chunk_document(source, config)
    second = chunk_document(source, config)

    assert first == second
    assert all(chunk.character_count <= 10 for chunk in first)
