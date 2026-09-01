"""Unit tests for reporting, visualization, and JSON/HTML export (Phase 10)."""

import json
import pytest
from pdf_comparator.core.models import (
    Chunk,
    ChunkType,
    ComparisonResult,
    MatchResult,
    MatchStatus,
    ProcessingStats,
    SeverityLevel,
)
from pdf_comparator.output.html_builder import HTMLReportBuilder
from pdf_comparator.output.json_builder import JSONReportBuilder


@pytest.fixture
def sample_result() -> ComparisonResult:
    """Fixture providing a mock ComparisonResult covering all match statuses, severities, and XSS cases."""
    chunk_a = Chunk(
        id="a1",
        paragraph_id="p1",
        original_text="The supplier must pay $10,000 within 30 days.",
        normalized_text="the supplier must pay $10,000 within 30 days.",
        page_num=1,
        bbox=(10.0, 20.0, 200.0, 50.0),
        type=ChunkType.TEXT,
    )
    chunk_b = Chunk(
        id="b1",
        paragraph_id="p1",
        original_text="The supplier may pay $12,000 within 45 days.",
        normalized_text="the supplier may pay $12,000 within 45 days.",
        page_num=1,
        bbox=(10.0, 20.0, 200.0, 50.0),
        type=ChunkType.TEXT,
    )

    match_modified = MatchResult(
        status=MatchStatus.MODIFIED,
        source_chunk=chunk_a,
        target_chunk=chunk_b,
        similarity_score=0.85,
        severity=SeverityLevel.HIGH,
        confidence=0.90,
        explanation="Modality term changed from 'must' to 'may'.; Currency amount changed from '$10,000' to '$12,000'.",
        structural_changes={
            "has_structural_changes": True,
            "changes": [
                {
                    "change_type": "modality_change",
                    "old_value": "must",
                    "new_value": "may",
                    "explanation": "Modality changed",
                },
                {
                    "change_type": "currency_change",
                    "old_value": "$10,000",
                    "new_value": "$12,000",
                    "explanation": "Currency changed",
                },
            ],
        },
    )

    match_unchanged = MatchResult(
        status=MatchStatus.UNCHANGED,
        source_chunk=Chunk("a2", "p2", "Header text", "header text", 1),
        target_chunk=Chunk("b2", "p2", "Header text", "header text", 1),
        similarity_score=1.0,
        severity=SeverityLevel.NONE,
        confidence=1.0,
        explanation="Exact normalized-text match.",
    )

    match_added = MatchResult(
        status=MatchStatus.ADDED,
        source_chunk=None,
        target_chunk=Chunk("b3", "p3", "Newly added section.", "newly added section.", 2),
        similarity_score=0.0,
        severity=SeverityLevel.LOW,
        confidence=0.90,
        explanation="Target chunk remained unmatched.",
    )

    match_xss = MatchResult(
        status=MatchStatus.REMOVED,
        source_chunk=Chunk("a4", "p4", "<script>alert('xss')</script>", "<script>alert('xss')</script>", 2),
        target_chunk=None,
        similarity_score=0.0,
        severity=SeverityLevel.MEDIUM,
        confidence=0.90,
        explanation="Untrusted text <iframe src='malicious'></iframe>",
    )

    stats = ProcessingStats(
        pages_processed=4,
        chunks_extracted=10,
        exact_matches=1,
        semantic_matches=1,
        added=1,
        removed=1,
        processing_time_ms=1250.0,
    )

    return ComparisonResult(
        source_document="doc_v1.pdf",
        target_document="doc_v2.pdf",
        results=[match_modified, match_unchanged, match_added, match_xss],
        stats=stats,
        timestamp="2026-09-01T22:30:00Z",
        engine_version="1.0.0",
    )


def test_json_builder_validity_and_enums(sample_result):
    """Test JSONReportBuilder generates valid JSON with serialized enums and bounding boxes."""
    builder = JSONReportBuilder()
    json_str = builder.build(sample_result)

    data = json.loads(json_str)
    assert data["source_document"] == "doc_v1.pdf"
    assert data["target_document"] == "doc_v2.pdf"

    summary = data["summary"]
    assert summary["modified"] == 1
    assert summary["unchanged"] == 1
    assert summary["added"] == 1
    assert summary["removed"] == 1
    assert summary["high"] == 1
    assert summary["medium"] == 1
    assert summary["low"] == 1

    first_res = data["results"][0]
    assert first_res["status"] == "modified"
    assert first_res["severity"] == "high"
    assert first_res["source_chunk"]["bbox"] == [10.0, 20.0, 200.0, 50.0]


def test_json_write_to_file(sample_result, tmp_path):
    """Test writing JSON report to disk."""
    builder = JSONReportBuilder()
    out_file = tmp_path / "reports" / "test_report.json"

    res_path = builder.write(sample_result, out_file)
    assert res_path.exists()

    content = json.loads(res_path.read_text(encoding="utf-8"))
    assert content["source_document"] == "doc_v1.pdf"


def test_html_builder_rendering_and_escaping(sample_result):
    """Test HTMLReportBuilder renders filenames, metadata, structural diffs, and escapes XSS content."""
    builder = HTMLReportBuilder()
    html_content = builder.build(sample_result)

    assert "doc_v1.pdf" in html_content
    assert "doc_v2.pdf" in html_content

    assert "MODIFIED" in html_content
    assert "UNCHANGED" in html_content
    assert "ADDED" in html_content
    assert "REMOVED" in html_content

    assert "SEVERITY: HIGH" in html_content
    assert "SEVERITY: MEDIUM" in html_content

    assert "MODALITY CHANGE" in html_content
    assert "CURRENCY CHANGE" in html_content

    # XSS escaping assertions
    assert "<script>alert('xss')</script>" not in html_content
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in html_content
    assert "<iframe" not in html_content


def test_html_builder_empty_results():
    """Test HTML generation for document comparison with 0 differences."""
    empty_result = ComparisonResult(
        source_document="empty_a.pdf",
        target_document="empty_b.pdf",
        results=[],
        stats=ProcessingStats(),
    )
    builder = HTMLReportBuilder()
    html_content = builder.build(empty_result)

    assert "No differences or comparison results found." in html_content


def test_html_write_to_file(sample_result, tmp_path):
    """Test writing HTML report to disk."""
    builder = HTMLReportBuilder()
    out_file = tmp_path / "reports" / "test_report.html"

    res_path = builder.write(sample_result, out_file)
    assert res_path.exists()

    text = res_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in text
