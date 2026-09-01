"""Unit tests for deterministic exact text matching."""

import time
from pdf_comparator.comparison.exact import ExactMatcher
from pdf_comparator.core.models import Chunk, ChunkType, MatchStatus, SeverityLevel


def make_chunk(
    chunk_id: str,
    text: str,
    norm_text: str = None,
    page_num: int = 1,
    paragraph_id: str = "p1",
) -> Chunk:
    """Helper function to construct Chunk instances for unit tests."""
    return Chunk(
        id=chunk_id,
        paragraph_id=paragraph_id,
        original_text=text,
        normalized_text=norm_text if norm_text is not None else text.strip().lower(),
        page_num=page_num,
        type=ChunkType.TEXT,
    )


def test_all_chunks_unchanged():
    """Test scenario where all chunks in A and B are identical exact matches."""
    cA1 = make_chunk("a1", "Payment is due in 30 days.")
    cA2 = make_chunk("a2", "The Contractor shall deliver the code.")

    cB1 = make_chunk("b1", "Payment is due in 30 days.")
    cB2 = make_chunk("b2", "The Contractor shall deliver the code.")

    matcher = ExactMatcher()
    res = matcher.match([cA1, cA2], [cB1, cB2])

    assert len(res.matched_results) == 2
    assert len(res.unmatched_chunks_a) == 0
    assert len(res.unmatched_chunks_b) == 0

    m1, m2 = res.matched_results[0], res.matched_results[1]
    assert m1.status == MatchStatus.UNCHANGED
    assert m1.similarity_score == 1.0
    assert m1.severity == SeverityLevel.NONE
    assert m1.confidence == 1.0
    assert m1.source_chunk.id == "a1"
    assert m1.target_chunk.id == "b1"


def test_added_candidate():
    """Test scenario where Document B contains an additional chunk not in A."""
    cA = make_chunk("a1", "Base clause.")
    cB1 = make_chunk("b1", "Base clause.")
    cB2 = make_chunk("b2", "New added clause.")

    matcher = ExactMatcher()
    res = matcher.match([cA], [cB1, cB2])

    assert len(res.matched_results) == 1
    assert len(res.unmatched_chunks_a) == 0
    assert len(res.unmatched_chunks_b) == 1
    assert res.unmatched_chunks_b[0].id == "b2"


def test_removed_candidate():
    """Test scenario where Document A contains a chunk removed in B."""
    cA1 = make_chunk("a1", "Base clause.")
    cA2 = make_chunk("a2", "Removed clause.")
    cB = make_chunk("b1", "Base clause.")

    matcher = ExactMatcher()
    res = matcher.match([cA1, cA2], [cB])

    assert len(res.matched_results) == 1
    assert len(res.unmatched_chunks_a) == 1
    assert len(res.unmatched_chunks_b) == 0
    assert res.unmatched_chunks_a[0].id == "a2"


def test_modified_candidate_remaining_unresolved():
    """Test scenario where modified text is left unmatched for semantic analysis."""
    cA = make_chunk("a1", "Payment is due in 30 days.")
    cB = make_chunk("b1", "Payment is due in 45 days.")

    matcher = ExactMatcher()
    res = matcher.match([cA], [cB])

    # Exact matcher should NOT force a match for non-identical text
    assert len(res.matched_results) == 0
    assert len(res.unmatched_chunks_a) == 1
    assert len(res.unmatched_chunks_b) == 1
    assert res.unmatched_chunks_a[0].id == "a1"
    assert res.unmatched_chunks_b[0].id == "b1"


def test_duplicate_text_handling():
    """Test duplicate text allocation: each B chunk consumed at most once."""
    cA1 = make_chunk("a1", "Payment due in 30 days.")
    cA2 = make_chunk("a2", "Payment due in 30 days.")  # Duplicate in A
    cB1 = make_chunk("b1", "Payment due in 30 days.")  # Only 1 in B

    matcher = ExactMatcher()
    res = matcher.match([cA1, cA2], [cB1])

    assert len(res.matched_results) == 1
    assert res.matched_results[0].source_chunk.id == "a1"
    assert res.matched_results[0].target_chunk.id == "b1"

    # Second A chunk must remain unmatched in pool A
    assert len(res.unmatched_chunks_a) == 1
    assert res.unmatched_chunks_a[0].id == "a2"
    assert len(res.unmatched_chunks_b) == 0


def test_reordered_identical_chunks():
    """Test identical chunk appearing on Page 2 in A and Page 7 in B."""
    cA = make_chunk("a1", "Reordered section clause.", page_num=2)
    cB = make_chunk("b1", "Reordered section clause.", page_num=7)

    matcher = ExactMatcher()
    res = matcher.match([cA], [cB])

    assert len(res.matched_results) == 1
    m = res.matched_results[0]
    assert m.status == MatchStatus.UNCHANGED
    assert m.source_chunk.page_num == 2
    assert m.target_chunk.page_num == 7
    assert "reordered from page 2 to page 7" in m.explanation


def test_empty_document_a():
    """Test matching when Document A is empty."""
    cB = make_chunk("b1", "Clause in B.")
    matcher = ExactMatcher()
    res = matcher.match([], [cB])

    assert len(res.matched_results) == 0
    assert len(res.unmatched_chunks_a) == 0
    assert len(res.unmatched_chunks_b) == 1
    assert res.unmatched_chunks_b[0].id == "b1"


def test_empty_document_b():
    """Test matching when Document B is empty."""
    cA = make_chunk("a1", "Clause in A.")
    matcher = ExactMatcher()
    res = matcher.match([cA], [])

    assert len(res.matched_results) == 0
    assert len(res.unmatched_chunks_a) == 1
    assert len(res.unmatched_chunks_b) == 0
    assert res.unmatched_chunks_a[0].id == "a1"


def test_both_documents_empty():
    """Test matching when both A and B are empty."""
    matcher = ExactMatcher()
    res = matcher.match([], [])

    assert len(res.matched_results) == 0
    assert len(res.unmatched_chunks_a) == 0
    assert len(res.unmatched_chunks_b) == 0


def test_whitespace_normalized_equivalent_content():
    """Test matching based on normalized_text despite original_text whitespace differences."""
    cA = Chunk(
        id="a1",
        paragraph_id="p1",
        original_text="Payment  is   due\nin 30  days.",
        normalized_text="payment is due in 30 days.",
        page_num=1,
    )
    cB = Chunk(
        id="b1",
        paragraph_id="p1",
        original_text="Payment is due in 30 days.",
        normalized_text="payment is due in 30 days.",
        page_num=1,
    )

    matcher = ExactMatcher()
    res = matcher.match([cA], [cB])

    assert len(res.matched_results) == 1
    m = res.matched_results[0]
    assert m.status == MatchStatus.UNCHANGED
    assert m.source_chunk.original_text == "Payment  is   due\nin 30  days."
    assert m.target_chunk.original_text == "Payment is due in 30 days."


def test_preservation_of_metadata_and_original_text():
    """Verify original text and chunk metadata are preserved untouched in MatchResult."""
    cA = Chunk(
        id="a1",
        paragraph_id="p1",
        original_text="Exact Text Original A",
        normalized_text="exact text original a",
        page_num=3,
        section="Section 2",
        bbox=(10.0, 20.0, 100.0, 50.0),
        metadata={"custom_key": "value_a"},
    )
    cB = Chunk(
        id="b1",
        paragraph_id="p1",
        original_text="Exact Text Original B",
        normalized_text="exact text original a",
        page_num=3,
        section="Section 2",
        bbox=(10.0, 20.0, 100.0, 50.0),
        metadata={"custom_key": "value_b"},
    )

    matcher = ExactMatcher()
    res = matcher.match([cA], [cB])

    assert len(res.matched_results) == 1
    m = res.matched_results[0]
    assert m.source_chunk.original_text == "Exact Text Original A"
    assert m.source_chunk.metadata == {"custom_key": "value_a"}
    assert m.target_chunk.metadata == {"custom_key": "value_b"}


def test_large_synthetic_chunk_list_performance():
    """Verify O(N + M) performance on a large dataset of 10,000 chunks."""
    num_chunks = 10000
    chunks_a = [
        make_chunk(f"a_{i}", f"Sentence number {i} in large document test.")
        for i in range(num_chunks)
    ]
    chunks_b = [
        make_chunk(f"b_{i}", f"Sentence number {i} in large document test.")
        for i in range(num_chunks)
    ]

    start_time = time.perf_counter()
    matcher = ExactMatcher()
    res = matcher.match(chunks_a, chunks_b)
    elapsed_time = time.perf_counter() - start_time

    assert len(res.matched_results) == num_chunks
    assert len(res.unmatched_chunks_a) == 0
    assert len(res.unmatched_chunks_b) == 0
    # Must complete 10,000 matches in less than 0.2 seconds due to O(N + M) indexing
    assert elapsed_time < 0.2
