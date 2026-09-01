"""Unit tests for pdf_comparator data models."""

from pdf_comparator.core.models import (
    Chunk,
    ChunkType,
    MatchResult,
    MatchStatus,
    ProcessingStats,
    SeverityLevel,
)


def test_chunk_creation_and_serialization():
    """Test Chunk creation, default values, and dict serialization roundtrip."""
    chunk = Chunk(
        id="docA_p1_c1",
        paragraph_id="docA_p1",
        original_text="The Payment shall be made within 30 days.",
        normalized_text="the payment shall be made within 30 days",
        page_num=1,
        section="Section 3.1",
        bbox=(10.0, 20.0, 100.0, 50.0),
        type=ChunkType.TEXT,
        metadata={"font": "Helvetica"},
    )

    assert chunk.id == "docA_p1_c1"
    assert chunk.paragraph_id == "docA_p1"
    assert chunk.original_text == "The Payment shall be made within 30 days."
    assert chunk.normalized_text == "the payment shall be made within 30 days"
    assert chunk.page_num == 1
    assert chunk.section == "Section 3.1"
    assert chunk.bbox == (10.0, 20.0, 100.0, 50.0)
    assert chunk.type == ChunkType.TEXT
    assert chunk.metadata == {"font": "Helvetica"}

    # Test serialization
    data = chunk.to_dict()
    assert data["type"] == "text"
    assert data["id"] == "docA_p1_c1"

    # Test deserialization
    reconstructed = Chunk.from_dict(data)
    assert reconstructed == chunk


def test_match_result_creation_and_serialization():
    """Test MatchResult with source and target chunks, and dict roundtrip."""
    source_chunk = Chunk(
        id="docA_p1_c1",
        paragraph_id="docA_p1",
        original_text="Payment within 30 days.",
        normalized_text="payment within 30 days",
        page_num=1,
    )

    target_chunk = Chunk(
        id="docB_p1_c1",
        paragraph_id="docB_p1",
        original_text="Payment within 45 days.",
        normalized_text="payment within 45 days",
        page_num=1,
    )

    result = MatchResult(
        status=MatchStatus.MODIFIED,
        source_chunk=source_chunk,
        target_chunk=target_chunk,
        similarity_score=0.92,
        structural_changes={"durations": {"old": ["30 days"], "new": ["45 days"]}},
        severity=SeverityLevel.HIGH,
        confidence=0.98,
        explanation="Semantic match aligned; HIGH severity due to changed payment duration.",
    )

    assert result.status == MatchStatus.MODIFIED
    assert result.source_chunk.id == "docA_p1_c1"
    assert result.target_chunk.id == "docB_p1_c1"
    assert result.similarity_score == 0.92
    assert result.severity == SeverityLevel.HIGH
    assert result.confidence == 0.98

    # Test serialization
    data = result.to_dict()
    assert data["status"] == "modified"
    assert data["severity"] == "high"
    assert data["source_chunk"]["id"] == "docA_p1_c1"
    assert data["target_chunk"]["id"] == "docB_p1_c1"

    # Test deserialization
    reconstructed = MatchResult.from_dict(data)
    assert reconstructed == result


def test_processing_stats_defaults_and_serialization():
    """Test ProcessingStats default values and dict serialization."""
    stats = ProcessingStats(
        pages_processed=4,
        chunks_extracted=120,
        exact_matches=90,
        semantic_matches=15,
        added=10,
        removed=5,
        ocr_pages=1,
        tables_detected=2,
        processing_time_ms=342.5,
    )

    assert stats.pages_processed == 4
    assert stats.tables_detected == 2
    assert stats.processing_time_ms == 342.5

    data = stats.to_dict()
    assert data["pages_processed"] == 4

    reconstructed = ProcessingStats.from_dict(data)
    assert reconstructed == stats


def test_enum_values():
    """Verify enum string values match expected domain vocabulary."""
    assert ChunkType.TABLE_CELL.value == "table_cell"
    assert MatchStatus.UNCHANGED.value == "unchanged"
    assert MatchStatus.ADDED.value == "added"
    assert MatchStatus.REMOVED.value == "removed"
    assert MatchStatus.MODIFIED.value == "modified"
    assert SeverityLevel.LOW.value == "low"
    assert SeverityLevel.MEDIUM.value == "medium"
    assert SeverityLevel.HIGH.value == "high"
