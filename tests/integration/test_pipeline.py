"""Integration tests for the end-to-end PDF comparison pipeline (Phase 9)."""

import os
import pytest
import fitz
from pdf_comparator.core.engine import ComparisonEngine
from pdf_comparator.core.models import MatchStatus, SeverityLevel
from pdf_comparator.ingestion.extractor import PDFExtractionError


def create_pdf(path: str, text_lines: list[str]) -> None:
    """Utility helper to generate synthetic PDFs programmatically using PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page()
    y = 50
    for line in text_lines:
        page.insert_text((50, y), line, fontsize=11)
        y += 25
    doc.save(path)
    doc.close()


@pytest.fixture
def temp_pdf_dir(tmp_path):
    """Fixture providing a temporary directory for synthetic test PDFs."""
    return tmp_path


def test_identical_pdfs(temp_pdf_dir):
    """Test comparing two identical PDFs produces 100% UNCHANGED results."""
    path_a = str(temp_pdf_dir / "doc_a.pdf")
    path_b = str(temp_pdf_dir / "doc_b.pdf")

    lines = ["Section 1. Agreement Terms", "The supplier shall deliver software in 30 days."]
    create_pdf(path_a, lines)
    create_pdf(path_b, lines)

    engine = ComparisonEngine()
    res = engine.compare(path_a, path_b)

    assert res.stats.pages_processed == 2
    assert res.stats.exact_matches == 2
    assert res.stats.added == 0
    assert res.stats.removed == 0
    assert all(r.status == MatchStatus.UNCHANGED for r in res.results)


def test_end_to_end_multichange_example(temp_pdf_dir):
    """Test required example: currency, duration, and modality changes in one sentence."""
    path_a = str(temp_pdf_dir / "contract_v1.pdf")
    path_b = str(temp_pdf_dir / "contract_v2.pdf")

    create_pdf(path_a, ["The supplier must pay $10,000 within 30 days."])
    create_pdf(path_b, ["The supplier may pay $12,000 within 45 days."])

    engine = ComparisonEngine()
    res = engine.compare(path_a, path_b)

    assert len(res.results) == 1
    match = res.results[0]
    assert match.status == MatchStatus.MODIFIED
    assert match.severity == SeverityLevel.HIGH

    struct_dict = match.structural_changes
    assert struct_dict.get("has_structural_changes") is True
    changes = struct_dict.get("changes", [])
    change_types = {c["change_type"] for c in changes}

    assert "currency_change" in change_types
    assert "duration_change" in change_types
    assert "modality_change" in change_types


def test_added_and_removed_paragraphs(temp_pdf_dir):
    """Test detection of added and removed paragraphs."""
    path_a = str(temp_pdf_dir / "v1.pdf")
    path_b = str(temp_pdf_dir / "v2.pdf")

    create_pdf(path_a, ["Common header text.", "Paragraph to be removed."])
    create_pdf(path_b, ["Common header text.", "Newly inserted paragraph."])

    engine = ComparisonEngine()
    res = engine.compare(path_a, path_b)

    statuses = [r.status for r in res.results]
    assert MatchStatus.UNCHANGED in statuses
    # Either aligned + modified or removed + added
    assert len(res.results) >= 2


def test_missing_files_raise_exception():
    """Test missing file path raises PDFExtractionError."""
    engine = ComparisonEngine()
    with pytest.raises(PDFExtractionError):
        engine.compare("non_existent_source.pdf", "non_existent_target.pdf")


def test_corrupt_pdf_file(temp_pdf_dir):
    """Test corrupt file raises PDFExtractionError."""
    corrupt_path = str(temp_pdf_dir / "corrupt.pdf")
    with open(corrupt_path, "wb") as f:
        f.write(b"NOT_A_VALID_PDF_HEADER")

    valid_path = str(temp_pdf_dir / "valid.pdf")
    create_pdf(valid_path, ["Valid text content."])

    engine = ComparisonEngine()
    with pytest.raises(PDFExtractionError):
        engine.compare(corrupt_path, valid_path)


def test_performance_timing_stats(temp_pdf_dir):
    """Test that processing stats include valid timing and page metrics."""
    path_a = str(temp_pdf_dir / "perf_a.pdf")
    path_b = str(temp_pdf_dir / "perf_b.pdf")

    create_pdf(path_a, ["Section 1.", "First paragraph.", "Second paragraph."])
    create_pdf(path_b, ["Section 1.", "First paragraph modified.", "Second paragraph."])

    engine = ComparisonEngine()
    res = engine.compare(path_a, path_b)

    assert res.stats.processing_time_ms > 0.0
    assert res.stats.pages_processed == 2
    assert res.stats.chunks_extracted == 6
