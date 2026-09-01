"""Unit tests for Phase 8 final classification, severity, and confidence scoring."""

from pdf_comparator.comparison.alignment import AlignedPair, AlignmentResult
from pdf_comparator.comparison.exact import ExactMatchResult
from pdf_comparator.comparison.semantic import CandidateMatch, SemanticRetrievalResult
from pdf_comparator.core.models import Chunk, ChunkType, MatchResult, MatchStatus, SeverityLevel
from pdf_comparator.scoring.classifier import ResultClassifier
from pdf_comparator.scoring.confidence import ConfidenceEvaluator
from pdf_comparator.scoring.severity import SeverityEvaluator


def make_chunk(chunk_id: str, text: str, page_num: int = 1) -> Chunk:
    """Helper to construct Chunk objects."""
    return Chunk(
        id=chunk_id,
        paragraph_id=f"p_{chunk_id}",
        original_text=text,
        normalized_text=text.strip().lower(),
        page_num=page_num,
        type=ChunkType.TEXT,
    )


def test_exact_match_classification():
    """Test exact match produces UNCHANGED status, NONE severity, and 1.0 confidence."""
    cA = make_chunk("a1", "Identical text.")
    cB = make_chunk("b1", "Identical text.")

    exact_res = ExactMatchResult(
        matched_results=[
            MatchResult(
                status=MatchStatus.UNCHANGED,
                source_chunk=cA,
                target_chunk=cB,
                similarity_score=1.0,
                severity=SeverityLevel.NONE,
                confidence=1.0,
            )
        ],
        unmatched_chunks_a=[],
        unmatched_chunks_b=[],
    )
    align_res = AlignmentResult([], [], [])

    classifier = ResultClassifier()
    results = classifier.classify(exact_res, align_res)

    assert len(results) == 1
    assert results[0].status == MatchStatus.UNCHANGED
    assert results[0].severity == SeverityLevel.NONE
    assert results[0].confidence == 1.0
    assert "Exact" in results[0].explanation


def test_normalized_equivalent_text():
    """Test normalized-equivalent pair produces UNCHANGED status."""
    cA = make_chunk("a1", "Text with  extra  space.")
    cB = make_chunk("b1", "Text with extra space.")
    # Force normalized_text equality
    cA.normalized_text = "text with extra space."
    cB.normalized_text = "text with extra space."

    pair = AlignedPair(
        source_chunk=cA,
        target_chunk=cB,
        source_id="a1",
        target_id="b1",
        semantic_score=0.95,
        lexical_score=1.0,
        section_score=1.0,
        type_score=1.0,
        numeric_entity_score=1.0,
        positional_score=1.0,
        composite_score=0.95,
        explanation="Matching text",
    )

    align_res = AlignmentResult([pair], [], [])
    exact_res = ExactMatchResult([], [], [])

    classifier = ResultClassifier()
    results = classifier.classify(exact_res, align_res)

    assert len(results) == 1
    assert results[0].status == MatchStatus.UNCHANGED
    assert results[0].severity == SeverityLevel.NONE


def test_simple_wording_change_low_severity():
    """Test simple wording change yields MODIFIED status with LOW severity."""
    cA = make_chunk("a1", "The software is fast.")
    cB = make_chunk("b1", "The application is quick.")

    pair = AlignedPair(
        source_chunk=cA,
        target_chunk=cB,
        source_id="a1",
        target_id="b1",
        semantic_score=0.80,
        lexical_score=0.40,
        section_score=0.5,
        type_score=1.0,
        numeric_entity_score=0.5,
        positional_score=1.0,
        composite_score=0.72,
        explanation="Moderate similarity",
    )

    align_res = AlignmentResult([pair], [], [])
    exact_res = ExactMatchResult([], [], [])

    classifier = ResultClassifier()
    results = classifier.classify(exact_res, align_res)

    assert len(results) == 1
    assert results[0].status == MatchStatus.MODIFIED
    assert results[0].severity == SeverityLevel.LOW


def test_currency_change_high_severity():
    """Test currency amount change yields MODIFIED status with HIGH severity."""
    cA = make_chunk("a1", "Total fee is $10,000.")
    cB = make_chunk("b1", "Total fee is $12,000.")

    pair = AlignedPair(
        source_chunk=cA,
        target_chunk=cB,
        source_id="a1",
        target_id="b1",
        semantic_score=0.85,
        lexical_score=0.75,
        section_score=1.0,
        type_score=1.0,
        numeric_entity_score=0.0,
        positional_score=1.0,
        composite_score=0.82,
        explanation="Matching section",
    )

    align_res = AlignmentResult([pair], [], [])
    exact_res = ExactMatchResult([], [], [])

    classifier = ResultClassifier()
    results = classifier.classify(exact_res, align_res)

    assert len(results) == 1
    assert results[0].status == MatchStatus.MODIFIED
    assert results[0].severity == SeverityLevel.HIGH
    assert "$10,000" in results[0].explanation


def test_modality_change_high_severity():
    """Test modality obligation shift (must -> may) yields HIGH severity."""
    cA = make_chunk("a1", "Supplier must deliver the goods.")
    cB = make_chunk("b1", "Supplier may deliver the goods.")

    pair = AlignedPair(
        source_chunk=cA,
        target_chunk=cB,
        source_id="a1",
        target_id="b1",
        semantic_score=0.85,
        lexical_score=0.75,
        section_score=1.0,
        type_score=1.0,
        numeric_entity_score=0.5,
        positional_score=1.0,
        composite_score=0.83,
        explanation="High similarity",
    )

    align_res = AlignmentResult([pair], [], [])
    exact_res = ExactMatchResult([], [], [])

    classifier = ResultClassifier()
    results = classifier.classify(exact_res, align_res)

    assert len(results) == 1
    assert results[0].status == MatchStatus.MODIFIED
    assert results[0].severity == SeverityLevel.HIGH
    assert "must" in results[0].explanation


def test_added_and_removed_chunks():
    """Test classification of unmatched ADDED and REMOVED chunks."""
    cA = make_chunk("a1", "Removed section text.")
    cB = make_chunk("b1", "Newly added section text.")

    align_res = AlignmentResult([], [cA], [cB])
    exact_res = ExactMatchResult([], [], [])

    classifier = ResultClassifier()
    results = classifier.classify(exact_res, align_res)

    assert len(results) == 2
    statuses = {r.status for r in results}
    assert MatchStatus.REMOVED in statuses
    assert MatchStatus.ADDED in statuses


def test_candidate_margin_boosts_confidence():
    """Test that a large candidate margin increases confidence score."""
    cA = make_chunk("a1", "Test chunk")
    cB1 = make_chunk("b1", "Test chunk target 1")
    cB2 = make_chunk("b2", "Test chunk target 2")

    retrieval_res = SemanticRetrievalResult(
        candidates_by_source={
            "a1": [
                CandidateMatch(cA, cB1, "a1", "b1", 0.90),
                CandidateMatch(cA, cB2, "a1", "b2", 0.60),  # Margin = 0.30 >= 0.20
            ]
        }
    )

    pair = AlignedPair(
        source_chunk=cA,
        target_chunk=cB1,
        source_id="a1",
        target_id="b1",
        semantic_score=0.90,
        lexical_score=0.80,
        section_score=1.0,
        type_score=1.0,
        numeric_entity_score=0.5,
        positional_score=1.0,
        composite_score=0.85,
        explanation="Strong match",
    )

    conf_eval = ConfidenceEvaluator()
    conf_with_margin = conf_eval.evaluate_aligned_confidence(pair, candidate_margin=0.30)
    conf_without_margin = conf_eval.evaluate_aligned_confidence(pair, candidate_margin=None)

    assert conf_with_margin > conf_without_margin


def test_deterministic_repeated_execution():
    """Test that repeated execution of classification produces identical output."""
    cA = make_chunk("a1", "Fee is $5,000.")
    cB = make_chunk("b1", "Fee is $6,000.")

    pair = AlignedPair(
        source_chunk=cA,
        target_chunk=cB,
        source_id="a1",
        target_id="b1",
        semantic_score=0.85,
        lexical_score=0.75,
        section_score=1.0,
        type_score=1.0,
        numeric_entity_score=0.0,
        positional_score=1.0,
        composite_score=0.82,
        explanation="Matching section",
    )

    align_res = AlignmentResult([pair], [], [])
    exact_res = ExactMatchResult([], [], [])

    classifier = ResultClassifier()
    run1 = classifier.classify(exact_res, align_res)[0].to_dict()
    run2 = classifier.classify(exact_res, align_res)[0].to_dict()

    assert run1 == run2
