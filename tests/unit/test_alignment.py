"""Unit tests for multi-signal candidate alignment and 1-to-1 correspondence matching."""

from pdf_comparator.comparison.alignment import CandidateAligner
from pdf_comparator.comparison.semantic import CandidateMatch, SemanticRetrievalResult
from pdf_comparator.core.models import Chunk, ChunkType


def make_chunk(
    chunk_id: str,
    text: str,
    page_num: int = 1,
    section: str = None,
    chunk_type: ChunkType = ChunkType.TEXT,
) -> Chunk:
    """Helper function to construct Chunk objects for testing."""
    return Chunk(
        id=chunk_id,
        paragraph_id=f"p_{chunk_id}",
        original_text=text,
        normalized_text=text.strip().lower(),
        page_num=page_num,
        section=section,
        type=chunk_type,
    )


def test_clear_paraphrase_selects_correct_candidate():
    """Test that a clear paraphrase with high semantic and lexical overlap is selected."""
    cA = make_chunk("a1", "The contractor shall deliver the software in 30 days.", section="Obligations")
    cB1 = make_chunk("b1", "The vendor shall supply the code in 30 days.", section="Obligations")
    cB2 = make_chunk("b2", "Cooking pasta requires boiling water.", section="Recipes")

    retrieval_res = SemanticRetrievalResult(
        candidates_by_source={
            "a1": [
                CandidateMatch(cA, cB1, "a1", "b1", 0.85),
                CandidateMatch(cA, cB2, "a1", "b2", 0.20),
            ]
        }
    )

    aligner = CandidateAligner()
    res = aligner.align(retrieval_res, [cA], [cB1, cB2])

    assert len(res.aligned_pairs) == 1
    assert res.aligned_pairs[0].target_id == "b1"
    assert res.aligned_pairs[0].composite_score > 0.7
    assert len(res.unaligned_chunks_a) == 0
    assert len(res.unaligned_chunks_b) == 1
    assert res.unaligned_chunks_b[0].id == "b2"


def test_lexical_context_resolves_ambiguous_semantic_match():
    """Test lexical and section signals resolving two candidates with identical semantic scores."""
    cA = make_chunk("a1", "Payment is due within 30 days of invoice.", section="Payment Terms")
    cB1 = make_chunk("b1", "Payment is due within 30 days of invoice.", section="Payment Terms") # Strong lexical & section
    cB2 = make_chunk("b2", "Remittance must occur after thirty days.", section="General")      # Weak lexical & section

    retrieval_res = SemanticRetrievalResult(
        candidates_by_source={
            "a1": [
                CandidateMatch(cA, cB1, "a1", "b1", 0.80),
                CandidateMatch(cA, cB2, "a1", "b2", 0.80),  # Tied semantic score
            ]
        }
    )

    aligner = CandidateAligner()
    res = aligner.align(retrieval_res, [cA], [cB1, cB2])

    assert len(res.aligned_pairs) == 1
    assert res.aligned_pairs[0].target_id == "b1"  # Lexical and section signals resolve tie


def test_section_mismatch_affects_ranking():
    """Test that conflicting section headers penalize composite score compared to matching sections."""
    cA = make_chunk("a1", "Delivery schedule is Monday.", section="Delivery")
    cB_match = make_chunk("b1", "Delivery occurs on Mondays.", section="Delivery")
    cB_mismatch = make_chunk("b2", "Delivery occurs on Mondays.", section="Termination")

    aligner = CandidateAligner()
    score_match = aligner.compute_composite_score(cA, cB_match, 0.80)["composite"]
    score_mismatch = aligner.compute_composite_score(cA, cB_mismatch, 0.80)["composite"]

    assert score_match > score_mismatch


def test_compatible_chunk_types_preferred():
    """Test that matching chunk types (HEADING ↔ HEADING) get higher score than mismatched types."""
    cA = make_chunk("a1", "Section 1. Terms", chunk_type=ChunkType.HEADING)
    cB_heading = make_chunk("b1", "1. Terms and Provisions", chunk_type=ChunkType.HEADING)
    cB_text = make_chunk("b2", "1. Terms and Provisions", chunk_type=ChunkType.TEXT)

    aligner = CandidateAligner()
    s_heading = aligner.compute_composite_score(cA, cB_heading, 0.85)["composite"]
    s_text = aligner.compute_composite_score(cA, cB_text, 0.85)["composite"]

    assert s_heading > s_text


def test_numeric_overlap_affects_ranking():
    """Test that matching numbers ($5,000 vs $5,000) boosts alignment over mismatched numbers ($5,000 vs $9,000)."""
    cA = make_chunk("a1", "Total fee is $5,000.00 for services.")
    cB1 = make_chunk("b1", "Service cost is $5,000.00 total.")
    cB2 = make_chunk("b2", "Service cost is $9,000.00 total.")

    aligner = CandidateAligner()
    score1 = aligner.compute_composite_score(cA, cB1, 0.85)["composite"]
    score2 = aligner.compute_composite_score(cA, cB2, 0.85)["composite"]

    assert score1 > score2


def test_page_movement_does_not_prevent_matching():
    """Test paragraph moving from Page 2 to Page 15 still matches if semantic & section signals are strong."""
    cA = make_chunk("a1", "Software license terms.", page_num=2, section="Licensing")
    cB = make_chunk("b1", "Software licensing terms.", page_num=15, section="Licensing")

    retrieval_res = SemanticRetrievalResult(
        candidates_by_source={"a1": [CandidateMatch(cA, cB, "a1", "b1", 0.90)]}
    )

    aligner = CandidateAligner()
    res = aligner.align(retrieval_res, [cA], [cB])

    assert len(res.aligned_pairs) == 1
    assert res.aligned_pairs[0].target_id == "b1"


def test_one_to_one_constraint():
    """Test that two source chunks cannot both be assigned to the same single target chunk."""
    cA1 = make_chunk("a1", "Payment within 30 days.", section="Terms")
    cA2 = make_chunk("a2", "Payment within 30 days.", section="Terms")
    cB = make_chunk("b1", "Payment is due in 30 days.", section="Terms")

    # Both A1 and A2 point to B1 as top candidate
    retrieval_res = SemanticRetrievalResult(
        candidates_by_source={
            "a1": [CandidateMatch(cA1, cB, "a1", "b1", 0.90)],
            "a2": [CandidateMatch(cA2, cB, "a2", "b1", 0.88)],
        }
    )

    aligner = CandidateAligner()
    res = aligner.align(retrieval_res, [cA1, cA2], [cB])

    # Exactly 1 pair aligned to B1 (a1 has higher composite score)
    assert len(res.aligned_pairs) == 1
    assert res.aligned_pairs[0].source_id == "a1"
    assert res.aligned_pairs[0].target_id == "b1"
    # a2 remains in unaligned_a
    assert len(res.unaligned_chunks_a) == 1
    assert res.unaligned_chunks_a[0].id == "a2"


def test_unresolved_source_when_below_min_threshold():
    """Test source chunk remains unaligned when candidate composite score is below min_alignment_score."""
    cA = make_chunk("a1", "Agreement for supply.")
    cB = make_chunk("b1", "Astronomy research paper.")

    retrieval_res = SemanticRetrievalResult(
        candidates_by_source={"a1": [CandidateMatch(cA, cB, "a1", "b1", 0.15)]}
    )

    aligner = CandidateAligner()
    res = aligner.align(retrieval_res, [cA], [cB], min_alignment_score=0.45)

    assert len(res.aligned_pairs) == 0
    assert len(res.unaligned_chunks_a) == 1
    assert len(res.unaligned_chunks_b) == 1


def test_deterministic_tie_breaking():
    """Test identical scores yield exact same alignment output across multiple runs."""
    cA = make_chunk("a1", "Identical test phrase.")
    cB1 = make_chunk("b1", "Identical test phrase.")
    cB2 = make_chunk("b2", "Identical test phrase.")

    retrieval_res = SemanticRetrievalResult(
        candidates_by_source={
            "a1": [
                CandidateMatch(cA, cB1, "a1", "b1", 0.90),
                CandidateMatch(cA, cB2, "a1", "b2", 0.90),
            ]
        }
    )

    aligner = CandidateAligner()
    run1 = aligner.align(retrieval_res, [cA], [cB1, cB2])
    run2 = aligner.align(retrieval_res, [cA], [cB1, cB2])

    assert run1.aligned_pairs[0].target_id == run2.aligned_pairs[0].target_id


def test_empty_candidate_list():
    """Test handling of empty candidates input."""
    cA = make_chunk("a1", "Text A")
    cB = make_chunk("b1", "Text B")
    retrieval_res = SemanticRetrievalResult(candidates_by_source={})

    aligner = CandidateAligner()
    res = aligner.align(retrieval_res, [cA], [cB])

    assert len(res.aligned_pairs) == 0
    assert len(res.unaligned_chunks_a) == 1
    assert len(res.unaligned_chunks_b) == 1


def test_metadata_and_explanations_preserved():
    """Test metadata preservation and human-readable explanation generation."""
    cA = make_chunk("a1", "Contractual terms.", section="Section 1")
    cB = make_chunk("b1", "Contractual terms.", section="Section 1")

    retrieval_res = SemanticRetrievalResult(
        candidates_by_source={"a1": [CandidateMatch(cA, cB, "a1", "b1", 0.95)]}
    )

    aligner = CandidateAligner()
    res = aligner.align(retrieval_res, [cA], [cB])

    assert len(res.aligned_pairs) == 1
    pair = res.aligned_pairs[0]
    assert pair.source_chunk.section == "Section 1"
    assert "high semantic similarity" in pair.explanation
    assert "matching section context" in pair.explanation
