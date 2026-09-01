"""Unit tests for PDFExtractor."""

import fitz
import pytest
from pdf_comparator.ingestion.extractor import (
    PDFExtractionError,
    PDFExtractor,
)


@pytest.fixture
def single_page_pdf(tmp_path):
    """Create a temporary single-page PDF with text."""
    pdf_path = tmp_path / "single_page.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 100), "Hello, PDF Comparison Engine!")
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def multi_page_pdf(tmp_path):
    """Create a temporary multi-page PDF with text on each page."""
    pdf_path = tmp_path / "multi_page.pdf"
    doc = fitz.open()
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 100), "Page 1 Content")
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((50, 100), "Page 2 Content")
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def empty_page_pdf(tmp_path):
    """Create a temporary PDF with a blank page."""
    pdf_path = tmp_path / "empty_page.pdf"
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def corrupt_pdf(tmp_path):
    """Create an unreadable corrupt PDF file."""
    pdf_path = tmp_path / "corrupt.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 invalid corrupt binary data")
    return pdf_path


def test_extract_single_page_pdf(single_page_pdf):
    """Verify single-page extraction text, bbox, and page metadata."""
    extractor = PDFExtractor()
    raw_doc = extractor.extract(single_page_pdf)

    assert raw_doc.total_pages == 1
    assert len(raw_doc.pages) == 1

    page = raw_doc.pages[0]
    assert page.page_num == 1
    assert page.width == 595.0
    assert page.height == 842.0
    assert page.has_text is True

    # Verify original text and bounding box preservation
    combined_text = "".join(b.text for b in page.blocks)
    assert "Hello, PDF Comparison Engine!" in combined_text
    assert len(page.blocks) > 0
    assert page.blocks[0].bbox[0] >= 0  # x0 valid
    assert page.blocks[0].bbox[1] >= 0  # y0 valid


def test_extract_multi_page_pdf(multi_page_pdf):
    """Verify multi-page PDF extraction and page numbering."""
    extractor = PDFExtractor()
    raw_doc = extractor.extract(multi_page_pdf)

    assert raw_doc.total_pages == 2
    assert len(raw_doc.pages) == 2

    assert raw_doc.pages[0].page_num == 1
    assert "Page 1 Content" in raw_doc.pages[0].blocks[0].text

    assert raw_doc.pages[1].page_num == 2
    assert "Page 2 Content" in raw_doc.pages[1].blocks[0].text


def test_extract_empty_page(empty_page_pdf):
    """Verify handling of blank pages without text."""
    extractor = PDFExtractor()
    raw_doc = extractor.extract(empty_page_pdf)

    assert raw_doc.total_pages == 1
    page = raw_doc.pages[0]
    assert page.page_num == 1
    assert page.has_text is False
    assert len(page.blocks) == 0


def test_extract_missing_file_raises_file_not_found(tmp_path):
    """Verify missing file paths raise FileNotFoundError."""
    extractor = PDFExtractor()
    missing_path = tmp_path / "non_existent.pdf"

    with pytest.raises(FileNotFoundError):
        extractor.extract(missing_path)


def test_extract_corrupt_pdf_raises_extraction_error(corrupt_pdf):
    """Verify corrupt/invalid PDF files raise PDFExtractionError."""
    extractor = PDFExtractor()

    with pytest.raises(PDFExtractionError):
        extractor.extract(corrupt_pdf)
