"""Unit tests for content-aware structural change detection (Phase 7)."""

from pdf_comparator.comparison.structural import (
    StructuralAnalyzer,
    StructuralChangeType,
)
from pdf_comparator.core.models import Chunk, ChunkType


def make_chunk(chunk_id: str, text: str, page_num: int = 1, section: str = None) -> Chunk:
    """Helper to create test Chunk objects."""
    return Chunk(
        id=chunk_id,
        paragraph_id=f"p_{chunk_id}",
        original_text=text,
        normalized_text=text.strip().lower(),
        page_num=page_num,
        section=section,
        type=ChunkType.TEXT,
    )


def test_no_structural_changes():
    """Test identical text produces no structural changes."""
    cA = make_chunk("a1", "The supplier will deliver the software on Monday.")
    cB = make_chunk("b1", "The supplier will deliver the software on Monday.")

    analyzer = StructuralAnalyzer()
    res = analyzer.analyze_pair(cA, cB)

    assert not res.has_structural_changes
    assert len(res.changes) == 0


def test_numeric_value_change():
    """Test simple integer value change detection."""
    cA = make_chunk("a1", "Minimum quantity is 100 items.")
    cB = make_chunk("b1", "Minimum quantity is 200 items.")

    analyzer = StructuralAnalyzer()
    res = analyzer.analyze_pair(cA, cB)

    assert res.has_structural_changes
    assert len(res.changes) == 1
    assert res.changes[0].change_type == StructuralChangeType.NUMBER_CHANGE
    assert res.changes[0].old_value == "100"
    assert res.changes[0].new_value == "200"


def test_decimal_number_change():
    """Test decimal value change detection."""
    cA = make_chunk("a1", "Weight parameter is 10.5 kg.")
    cB = make_chunk("b1", "Weight parameter is 12.8 kg.")

    analyzer = StructuralAnalyzer()
    res = analyzer.analyze_pair(cA, cB)

    assert res.has_structural_changes
    # Either unit or number change
    assert res.changes[0].change_type in (StructuralChangeType.UNIT_CHANGE, StructuralChangeType.NUMBER_CHANGE)


def test_currency_change():
    """Test currency change detection ($10,000 -> $12,000)."""
    cA = make_chunk("a1", "Total fee is $10,000.00 for project.")
    cB = make_chunk("b1", "Total fee is $12,000.00 for project.")

    analyzer = StructuralAnalyzer()
    res = analyzer.analyze_pair(cA, cB)

    assert res.has_structural_changes
    assert len(res.changes) == 1
    assert res.changes[0].change_type == StructuralChangeType.CURRENCY_CHANGE
    assert "$10,000" in res.changes[0].old_value
    assert "$12,000" in res.changes[0].new_value


def test_percentage_change():
    """Test percentage change detection (5% -> 8%)."""
    cA = make_chunk("a1", "Annual interest rate is 5%.")
    cB = make_chunk("b1", "Annual interest rate is 8%.")

    analyzer = StructuralAnalyzer()
    res = analyzer.analyze_pair(cA, cB)

    assert res.has_structural_changes
    assert len(res.changes) == 1
    assert res.changes[0].change_type == StructuralChangeType.PERCENTAGE_CHANGE


def test_date_change():
    """Test date value change detection."""
    cA = make_chunk("a1", "Effective date is 1 January 2026.")
    cB = make_chunk("b1", "Effective date is 15 January 2026.")

    analyzer = StructuralAnalyzer()
    res = analyzer.analyze_pair(cA, cB)

    assert res.has_structural_changes
    assert len(res.changes) == 1
    assert res.changes[0].change_type == StructuralChangeType.DATE_CHANGE


def test_equivalent_date_formatting_no_false_change():
    """Test '1 January 2026' vs 'January 1, 2026' produces NO date change."""
    cA = make_chunk("a1", "Effective date is 1 January 2026.")
    cB = make_chunk("b1", "Effective date is January 1, 2026.")

    analyzer = StructuralAnalyzer()
    res = analyzer.analyze_pair(cA, cB)

    assert not res.has_structural_changes


def test_duration_change():
    """Test duration value change detection (30 days -> 45 days)."""
    cA = make_chunk("a1", "Payment is due within 30 days of invoice.")
    cB = make_chunk("b1", "Payment is due within 45 days of invoice.")

    analyzer = StructuralAnalyzer()
    res = analyzer.analyze_pair(cA, cB)

    assert res.has_structural_changes
    assert len(res.changes) == 1
    assert res.changes[0].change_type == StructuralChangeType.DURATION_CHANGE


def test_equivalent_written_duration_no_false_change():
    """Test 'within thirty days' vs 'within 30 days' produces NO duration change."""
    cA = make_chunk("a1", "Payment is due within thirty days of invoice.")
    cB = make_chunk("b1", "Payment is due within 30 days of invoice.")

    analyzer = StructuralAnalyzer()
    res = analyzer.analyze_pair(cA, cB)

    assert not res.has_structural_changes


def test_unit_change():
    """Test unit change detection (10 kg -> 10 g)."""
    cA = make_chunk("a1", "Package size is 10 kg.")
    cB = make_chunk("b1", "Package size is 10 g.")

    analyzer = StructuralAnalyzer()
    res = analyzer.analyze_pair(cA, cB)

    assert res.has_structural_changes
    assert len(res.changes) == 1
    assert res.changes[0].change_type == StructuralChangeType.UNIT_CHANGE


def test_modality_change():
    """Test modality term change detection ('must' -> 'may')."""
    cA = make_chunk("a1", "Supplier must deliver software.")
    cB = make_chunk("b1", "Supplier may deliver software.")

    analyzer = StructuralAnalyzer()
    res = analyzer.analyze_pair(cA, cB)

    assert res.has_structural_changes
    assert len(res.changes) == 1
    assert res.changes[0].change_type == StructuralChangeType.MODALITY_CHANGE
    assert res.changes[0].old_value == "must"
    assert res.changes[0].new_value == "may"


def test_added_structured_entity():
    """Test detection of newly added structured duration entity."""
    cA = make_chunk("a1", "Payment is due.")
    cB = make_chunk("b1", "Payment is due within 30 days.")

    analyzer = StructuralAnalyzer()
    res = analyzer.analyze_pair(cA, cB)

    assert res.has_structural_changes
    assert len(res.changes) == 1
    assert res.changes[0].change_type == StructuralChangeType.ENTITY_ADDED


def test_removed_structured_entity():
    """Test detection of removed structured duration entity."""
    cA = make_chunk("a1", "Payment is due within 30 days.")
    cB = make_chunk("b1", "Payment is due.")

    analyzer = StructuralAnalyzer()
    res = analyzer.analyze_pair(cA, cB)

    assert res.has_structural_changes
    assert len(res.changes) == 1
    assert res.changes[0].change_type == StructuralChangeType.ENTITY_REMOVED


def test_multiple_changes_in_one_chunk():
    """Test multiple entity changes in a single chunk ($10,000 within 30 days -> $12,000 within 45 days)."""
    cA = make_chunk("a1", "Customer must pay $10,000 within 30 days.")
    cB = make_chunk("b1", "Customer must pay $12,000 within 45 days.")

    analyzer = StructuralAnalyzer()
    res = analyzer.analyze_pair(cA, cB)

    assert res.has_structural_changes
    assert len(res.changes) == 2
    types = {c.change_type for c in res.changes}
    assert StructuralChangeType.CURRENCY_CHANGE in types
    assert StructuralChangeType.DURATION_CHANGE in types


def test_empty_source_or_target_text():
    """Test handling of empty source or target text."""
    cA = make_chunk("a1", "Some text")

    analyzer = StructuralAnalyzer()
    res = analyzer.analyze_pair(cA, None)

    assert res.source_chunk_id == "a1"


def test_section_page_numbering_no_false_change():
    """Test section numbers like 'Section 1' vs 'Section 2' ignore structural false positives when main text matches."""
    cA = make_chunk("a1", "General policy rules for Section 1.")
    cB = make_chunk("b1", "General policy rules for Section 2.")

    analyzer = StructuralAnalyzer()
    res = analyzer.analyze_pair(cA, cB)

    # Section numbers ignored by standalone number extractor
    assert len(res.changes) == 0


def test_deterministic_serialization():
    """Test to_dict serialization of StructuralChangeResult."""
    cA = make_chunk("a1", "Supplier must deliver.")
    cB = make_chunk("b1", "Supplier may deliver.")

    analyzer = StructuralAnalyzer()
    res = analyzer.analyze_pair(cA, cB)
    d = res.to_dict()

    assert d["source_chunk_id"] == "a1"
    assert d["target_chunk_id"] == "b1"
    assert d["has_structural_changes"] is True
    assert len(d["changes"]) == 1
    assert d["changes"][0]["change_type"] == "modality_change"
