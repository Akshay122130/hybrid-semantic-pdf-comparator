"""Adversarial, edge-case, determinism, and false-positive protection unit tests (Phase 11)."""

import pytest
import fitz
from pdf_comparator.comparison.alignment import CandidateAligner
from pdf_comparator.comparison.exact import ExactMatcher
from pdf_comparator.comparison.structural import StructuralAnalyzer, StructuralChangeType
from pdf_comparator.core.engine import ComparisonEngine
from pdf_comparator.core.models import (
    Chunk,
    ChunkType,
    ComparisonResult,
    MatchResult,
    MatchStatus,
    SeverityLevel,
)
from pdf_comparator.ingestion.extractor import PDFExtractor
from pdf_comparator.output.html_builder import HTMLReportBuilder
from pdf_comparator.output.json_builder import JSONReportBuilder
from pdf_comparator.processing.cleaner import clean_text
from pdf_comparator.processing.segmenter import DocumentSegmenter


def create_pdf(path: str, pages_content: list[list[str]]) -> None:
    """Helper to create multi-page synthetic PDFs."""
    doc = fitz.open()
    for lines in pages_content:
        page = doc.new_page()
        y = 50
        for line in lines:
            page.insert_text((50, y), line, fontsize=11)
            y += 25
    doc.save(path)
    doc.close()


# 1. FALSE-POSITIVE PROTECTION TESTS
def test_false_positive_section_and_page_numbering():
    """Verify Section, Page, and List numbers do NOT trigger false structural entity changes."""
    analyzer = StructuralAnalyzer()

    # Section numbers
    chunk_a = Chunk("a1", "p1", "Section 1. Agreement Scope and Obligations.", "section 1. agreement scope and obligations.", 1)
    chunk_b = Chunk("b1", "p1", "Section 2. Agreement Scope and Obligations.", "section 2. agreement scope and obligations.", 1)
    res = analyzer.analyze_pair(chunk_a, chunk_b)
    # Section heading changes should not be flagged as critical monetary/number changes
    assert not any(c.change_type == StructuralChangeType.NUMBER_CHANGE for c in res.changes)

    # Paragraph list numbering
    chunk_c = Chunk("a2", "p2", "1. First requirement.", "1. first requirement.", 1)
    chunk_d = Chunk("b2", "p2", "2. First requirement.", "2. first requirement.", 1)
    res_list = analyzer.analyze_pair(chunk_c, chunk_d)
    assert not any(c.change_type == StructuralChangeType.NUMBER_CHANGE for c in res_list.changes)


def test_formatting_equivalence_no_structural_change():
    """Verify equivalent date, duration, and number formats do NOT produce structural changes."""
    analyzer = StructuralAnalyzer()

    # Date formatting equivalence
    c1 = Chunk("a", "p", "Effective on 1 January 2026.", "effective on 1 january 2026.", 1)
    c2 = Chunk("b", "p", "Effective on January 1, 2026.", "effective on january 1, 2026.", 1)
    res_date = analyzer.analyze_pair(c1, c2)
    assert not res_date.has_structural_changes

    # Duration written word vs digit equivalence
    c3 = Chunk("a", "p", "Delivered in 30 days.", "delivered in 30 days.", 1)
    c4 = Chunk("b", "p", "Delivered in thirty days.", "delivered in thirty days.", 1)
    res_dur = analyzer.analyze_pair(c3, c4)
    assert not res_dur.has_structural_changes


# 2. STRUCTURAL ENTITY ANALYSIS EDGE CASES
def test_multiple_structural_changes_in_one_chunk():
    """Verify detecting multiple changes (currency, duration, date, modality) in a single chunk."""
    analyzer = StructuralAnalyzer()
    src = Chunk("a", "p", "The client must pay $10,000 within 30 days by 1 January 2026.", "the client must pay $10,000 within 30 days by 1 january 2026.", 1)
    tgt = Chunk("b", "p", "The client may pay $15,000 within 60 days by 15 January 2026.", "the client may pay $15,000 within 60 days by 15 january 2026.", 1)

    res = analyzer.analyze_pair(src, tgt)
    assert res.has_structural_changes
    change_types = {c.change_type for c in res.changes}

    assert StructuralChangeType.MODALITY_CHANGE in change_types
    assert StructuralChangeType.CURRENCY_CHANGE in change_types
    assert StructuralChangeType.DURATION_CHANGE in change_types
    assert StructuralChangeType.DATE_CHANGE in change_types


# 3. EXTRACTION AND SEGMENTATION EDGE CASES
def test_blank_page_and_whitespace_handling(tmp_path):
    """Test PDF extraction and segmentation on blank pages and pages with unusual whitespace."""
    pdf_path = str(tmp_path / "blank.pdf")
    create_pdf(pdf_path, [
        [],  # Blank page 1
        ["   \n\t  \n  "],  # Whitespace-only page 2
        ["Valid text paragraph on page 3."]  # Page 3
    ])

    extractor = PDFExtractor()
    raw_doc = extractor.extract(pdf_path)
    assert raw_doc.total_pages == 3

    segmenter = DocumentSegmenter()
    chunks = segmenter.segment(raw_doc)
    assert len(chunks) == 1
    assert chunks[0].page_num == 3
    assert chunks[0].original_text == "Valid text paragraph on page 3."


def test_long_paragraph_cleaner_and_segmenter():
    """Test cleaning and segmenting very long text content."""
    long_text = "Word " * 500 + ". " + "Sentence two " * 300 + "."
    cleaned = clean_text(long_text)
    assert "  " not in cleaned  # No double spaces

    raw_doc = fitz.open()
    p = raw_doc.new_page()
    p.insert_text((50, 50), long_text[:500], fontsize=10)
    
    from pdf_comparator.ingestion.extractor import RawBlock, RawDocument, RawPage
    raw_document = RawDocument(
        file_path="test.pdf",
        total_pages=1,
        pages=[RawPage(page_num=1, width=600.0, height=800.0, blocks=[RawBlock(0, long_text, (0, 0, 100, 100))], has_text=True)],
    )

    chunks = DocumentSegmenter().segment(raw_document)
    assert len(chunks) >= 2  # Split into multiple sentences


# 4. DETERMINISM VERIFICATION TEST
def test_deterministic_pipeline_execution(tmp_path):
    """Verify that running the comparison engine 5 times produces identical MatchResult output."""
    path_a = str(tmp_path / "doc_a.pdf")
    path_b = str(tmp_path / "doc_b.pdf")

    create_pdf(path_a, [["The supplier must pay $10,000 within 30 days.", "Unchanged agreement terms."]])
    create_pdf(path_b, [["The supplier may pay $12,000 within 45 days.", "Unchanged agreement terms."]])

    engine = ComparisonEngine()

    results_history = []
    for _ in range(5):
        res = engine.compare(path_a, path_b)
        res_dict = res.to_dict()
        res_dict["stats"]["processing_time_ms"] = 0.0
        res_dict["timestamp"] = ""
        results_history.append(res_dict)

    first_res = results_history[0]
    for i in range(1, 5):
        assert results_history[i] == first_res


# 5. ADVERSARIAL HTML ESCAPING TEST
def test_adversarial_xss_in_all_fields():
    """Verify malicious XSS strings in source, target, section, and explanations are safely escaped."""
    xss_payload = "<script>alert('hack');</script><img src=x onerror=alert(1)>"
    chunk_a = Chunk("a", "p", xss_payload, xss_payload, 1, section=xss_payload)
    chunk_b = Chunk("b", "p", xss_payload, xss_payload, 1, section=xss_payload)

    match = MatchResult(
        status=MatchStatus.MODIFIED,
        source_chunk=chunk_a,
        target_chunk=chunk_b,
        similarity_score=0.5,
        severity=SeverityLevel.HIGH,
        confidence=0.5,
        explanation=xss_payload,
    )

    res = ComparisonResult(
        source_document=xss_payload,
        target_document=xss_payload,
        results=[match],
    )

    builder = HTMLReportBuilder()
    html_out = builder.build(res)

    import html
    assert xss_payload not in html_out
    assert html.escape(xss_payload) in html_out
