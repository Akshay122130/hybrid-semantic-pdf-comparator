"""Document ingestion module."""

from pdf_comparator.ingestion.extractor import (
    PDFExtractionError,
    PDFExtractor,
    RawBlock,
    RawDocument,
    RawPage,
)

__all__ = [
    "PDFExtractionError",
    "PDFExtractor",
    "RawBlock",
    "RawDocument",
    "RawPage",
]
