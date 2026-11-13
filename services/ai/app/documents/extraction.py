from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from pathlib import PurePath

import fitz
from docx import Document
from docx.document import Document as DocumentType
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from openpyxl import load_workbook

from app.documents.exceptions import (
    DocumentExtractionError,
    EmptyDocumentError,
    UnsupportedDocumentError,
)
from app.documents.models import ExtractedDocument, ExtractedSegment
from app.documents.normalization import normalize_text

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".csv", ".txt"}


def extract_document(content: bytes, filename: str) -> ExtractedDocument:
    """Extract searchable text and source metadata from supported file content."""
    extension = PurePath(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedDocumentError(
            f"Unsupported document format: {extension or '<missing extension>'}."
        )
    if not content:
        raise EmptyDocumentError(f"{filename} is empty.")

    extractors = {
        ".pdf": _extract_pdf,
        ".docx": _extract_docx,
        ".xlsx": _extract_xlsx,
        ".csv": _extract_csv,
        ".txt": _extract_txt,
    }
    try:
        segments = tuple(extractors[extension](content))
    except DocumentExtractionError:
        raise
    except Exception as error:
        raise DocumentExtractionError(
            f"Could not extract content from {filename}: {error}"
        ) from error

    if not any(normalize_text(segment.text) for segment in segments):
        raise EmptyDocumentError(f"{filename} contains no extractable text.")
    return ExtractedDocument(
        filename=filename,
        file_type=extension.removeprefix("."),
        segments=segments,
    )


def _extract_pdf(content: bytes) -> Iterator[ExtractedSegment]:
    try:
        with fitz.open(stream=content, filetype="pdf") as document:
            found_text = False
            for page_number, page in enumerate(document, start=1):
                text = page.get_text("text")
                if normalize_text(text):
                    found_text = True
                    yield ExtractedSegment(text=text, page_number=page_number)
            if not found_text:
                raise EmptyDocumentError(
                    "PDF contains no extractable text; OCR is not supported."
                )
    except Exception as error:
        if isinstance(error, DocumentExtractionError):
            raise
        raise DocumentExtractionError(f"Could not read PDF content: {error}") from error


def _iter_docx_blocks(parent: DocumentType | _Cell) -> Iterator[Paragraph | Table]:
    parent_element = (
        parent.element.body if isinstance(parent, DocumentType) else parent._tc
    )
    for child in parent_element.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def _extract_docx(content: bytes) -> Iterator[ExtractedSegment]:
    try:
        document = Document(io.BytesIO(content))
        current_section: str | None = None
        for block in _iter_docx_blocks(document):
            if isinstance(block, Paragraph):
                text = normalize_text(block.text)
                if not text:
                    continue
                if block.style.name.startswith("Heading"):
                    current_section = text
                yield ExtractedSegment(text=text, section_name=current_section)
            else:
                for row in block.rows:
                    values = [normalize_text(cell.text) for cell in row.cells]
                    row_text = " | ".join(value for value in values if value)
                    if row_text:
                        yield ExtractedSegment(
                            text=row_text,
                            section_name=current_section,
                        )
    except Exception as error:
        raise DocumentExtractionError(
            f"Could not read DOCX content: {error}"
        ) from error


def _extract_xlsx(content: bytes) -> Iterator[ExtractedSegment]:
    workbook = None
    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        for worksheet in workbook.worksheets:
            for row in worksheet.iter_rows():
                values = [
                    f"{cell.coordinate}: {cell.value}"
                    for cell in row
                    if cell.value is not None and str(cell.value).strip()
                ]
                if values:
                    yield ExtractedSegment(
                        text=" | ".join(values),
                        sheet_name=worksheet.title,
                    )
    except Exception as error:
        raise DocumentExtractionError(
            f"Could not read XLSX content: {error}"
        ) from error
    finally:
        if workbook is not None:
            workbook.close()


def _extract_csv(content: bytes) -> Iterator[ExtractedSegment]:
    try:
        text = content.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text, newline="")))
    except (UnicodeDecodeError, csv.Error) as error:
        raise DocumentExtractionError(f"Could not read CSV content: {error}") from error

    if not rows:
        return
    headers = [
        header.strip() or f"Column {index + 1}" for index, header in enumerate(rows[0])
    ]
    for row_number, row in enumerate(rows[1:], start=2):
        values = [
            f"{headers[index] if index < len(headers) else f'Column {index + 1}'}: "
            f"{value}"
            for index, value in enumerate(row)
            if value.strip()
        ]
        if values:
            yield ExtractedSegment(
                text=" | ".join(values),
                section_name=f"CSV row {row_number}",
            )
    if len(rows) == 1:
        header_text = " | ".join(f"{header}: " for header in headers)
        if header_text.strip():
            yield ExtractedSegment(text=header_text, section_name="CSV header")


def _extract_txt(content: bytes) -> Iterator[ExtractedSegment]:
    try:
        yield ExtractedSegment(text=content.decode("utf-8-sig"))
    except UnicodeDecodeError as error:
        raise DocumentExtractionError(
            f"Could not decode TXT content as UTF-8: {error}"
        ) from error
