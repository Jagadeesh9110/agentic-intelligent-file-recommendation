class DocumentExtractionError(ValueError):
    """Raised when a supported document cannot be extracted."""


class EmptyDocumentError(DocumentExtractionError):
    """Raised when a document contains no extractable text."""


class UnsupportedDocumentError(DocumentExtractionError):
    """Raised when a filename does not identify a supported format."""
