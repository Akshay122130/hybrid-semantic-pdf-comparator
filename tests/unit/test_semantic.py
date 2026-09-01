"""Unit tests for semantic candidate retrieval using SentenceTransformers and FAISS."""

from unittest.mock import MagicMock
import numpy as np
import pytest
from pdf_comparator.comparison.semantic import (
    CandidateMatch,
    SemanticRetrievalResult,
    SemanticRetriever,
)
from pdf_comparator.core.models import Chunk, ChunkType


def make_chunk(chunk_id: str, text: str, page_num: int = 1) -> Chunk:
    """Helper function to create test Chunk instances."""
    return Chunk(
        id=chunk_id,
        paragraph_id=f"p_{chunk_id}",
        original_text=text,
        normalized_text=text.strip().lower(),
        page_num=page_num,
        type=ChunkType.TEXT,
    )


@pytest.fixture(scope="module")
def shared_retriever():
    """Module-scoped fixture to instantiate SentenceTransformer once for real model tests."""
    return SemanticRetriever(model_name="all-MiniLM-L6-v2")


def test_paraphrase_higher_similarity_than_unrelated(shared_retriever):
    """Test that paraphrased text produces higher similarity than unrelated text."""
    cA = make_chunk("a1", "The supplier must deliver the software within 30 days.")
    cB1 = make_chunk("b1", "The vendor shall supply the code within thirty days.")  # Paraphrase
    cB2 = make_chunk("b2", "Cooking pasta requires boiling water and salt.")       # Unrelated

    res = shared_retriever.retrieve_candidates([cA], [cB1, cB2], top_k=2)
    candidates = res.get_candidates("a1")

    assert len(candidates) == 2
    # First candidate must be the paraphrase
    assert candidates[0].target_id == "b1"
    assert candidates[1].target_id == "b2"
    assert candidates[0].similarity_score > candidates[1].similarity_score
    assert candidates[0].similarity_score > 0.7


def test_unrelated_sentences_produce_low_similarity(shared_retriever):
    """Test that clearly unrelated sentences produce low similarity scores."""
    cA = make_chunk("a1", "The financial interest rates increased significantly.")
    cB = make_chunk("b1", "Bicycles have two wheels and pedals.")

    res = shared_retriever.retrieve_candidates([cA], [cB], top_k=1)
    candidates = res.get_candidates("a1")

    assert len(candidates) == 1
    assert candidates[0].similarity_score < 0.4


def test_top_k_retrieval(shared_retriever):
    """Test top-k candidate limit enforcement."""
    cA = make_chunk("a1", "Agreement terms and conditions.")
    targets = [
        make_chunk("b1", "Contractual terms and provisions."),
        make_chunk("b2", "Agreement rules and conditions."),
        make_chunk("b3", "Financial report statement."),
        make_chunk("b4", "Weather forecast for tomorrow."),
    ]

    res = shared_retriever.retrieve_candidates([cA], targets, top_k=2)
    candidates = res.get_candidates("a1")

    assert len(candidates) == 2
    assert candidates[0].similarity_score >= candidates[1].similarity_score


def test_top_k_larger_than_target_count(shared_retriever):
    """Test top_k larger than available target candidates."""
    cA = make_chunk("a1", "Test clause.")
    targets = [make_chunk("b1", "Test clause B1."), make_chunk("b2", "Test clause B2.")]

    res = shared_retriever.retrieve_candidates([cA], targets, top_k=10)
    candidates = res.get_candidates("a1")

    assert len(candidates) == 2


def test_minimum_similarity_filtering(shared_retriever):
    """Test filtering candidates by minimum similarity threshold."""
    cA = make_chunk("a1", "Software license agreement.")
    cB1 = make_chunk("b1", "Software licensing terms.")       # High similarity
    cB2 = make_chunk("b2", "Astronomy and galaxy evolution.")  # Low similarity

    res = shared_retriever.retrieve_candidates([cA], [cB1, cB2], top_k=5, minimum_similarity=0.6)
    candidates = res.get_candidates("a1")

    assert len(candidates) == 1
    assert candidates[0].target_id == "b1"


def test_empty_source_input(shared_retriever):
    """Test empty source list returns empty candidates dict."""
    cB = make_chunk("b1", "Some target text.")
    res = shared_retriever.retrieve_candidates([], [cB])
    assert res.candidates_by_source == {}


def test_empty_target_input(shared_retriever):
    """Test empty target list returns empty candidate list for source."""
    cA = make_chunk("a1", "Some source text.")
    res = shared_retriever.retrieve_candidates([cA], [])
    assert res.get_candidates("a1") == []


def test_duplicate_target_chunks(shared_retriever):
    """Test duplicate target chunks are preserved and returned as candidate options."""
    cA = make_chunk("a1", "Payment term.")
    cB1 = make_chunk("b1", "Payment term.")
    cB2 = make_chunk("b2", "Payment term.")

    res = shared_retriever.retrieve_candidates([cA], [cB1, cB2], top_k=2)
    candidates = res.get_candidates("a1")

    assert len(candidates) == 2
    assert {c.target_id for c in candidates} == {"b1", "b2"}


def test_metadata_and_chunk_preservation(shared_retriever):
    """Test that source and target Chunk objects and metadata are preserved in CandidateMatch."""
    cA = Chunk(
        id="a1",
        paragraph_id="p1",
        original_text="Original A",
        normalized_text="original a",
        page_num=2,
        metadata={"sec": "A"},
    )
    cB = Chunk(
        id="b1",
        paragraph_id="p1",
        original_text="Original B",
        normalized_text="original b",
        page_num=4,
        metadata={"sec": "B"},
    )

    res = shared_retriever.retrieve_candidates([cA], [cB], top_k=1)
    candidates = res.get_candidates("a1")

    assert len(candidates) == 1
    match = candidates[0]
    assert match.source_chunk.page_num == 2
    assert match.target_chunk.page_num == 4
    assert match.source_chunk.metadata == {"sec": "A"}
    assert match.target_chunk.metadata == {"sec": "B"}


def test_similarity_scores_in_cosine_range(shared_retriever):
    """Test similarity scores remain strictly within [-1.0, 1.0]."""
    cA = make_chunk("a1", "Random test sentence.")
    cB = make_chunk("b1", "Another sentence.")

    res = shared_retriever.retrieve_candidates([cA], [cB])
    candidates = res.get_candidates("a1")

    assert len(candidates) == 1
    assert -1.0 <= candidates[0].similarity_score <= 1.0


def test_model_loaded_once_and_reused():
    """Test model instance caching across multiple queries."""
    mock_model = MagicMock()
    # Mock encode method returning normalized 2D embeddings
    mock_model.encode.side_effect = lambda texts, **kwargs: np.ones((len(texts), 384), dtype=np.float32) / np.sqrt(384)

    retriever = SemanticRetriever(model_instance=mock_model)

    cA = make_chunk("a1", "Source text.")
    cB = make_chunk("b1", "Target text.")

    # Call twice
    retriever.retrieve_candidates([cA], [cB])
    retriever.retrieve_candidates([cA], [cB])

    # Verify model getter reused pre-instantiated model
    assert retriever._get_model() == mock_model


def test_multiple_source_queries_reuse_same_target_index(shared_retriever):
    """Test multiple source chunks querying the target FAISS index simultaneously."""
    cA1 = make_chunk("a1", "First query sentence.")
    cA2 = make_chunk("a2", "Second query sentence.")
    cB = make_chunk("b1", "First target sentence.")

    res = shared_retriever.retrieve_candidates([cA1, cA2], [cB], top_k=1)

    assert "a1" in res.candidates_by_source
    assert "a2" in res.candidates_by_source
    assert len(res.get_candidates("a1")) == 1
    assert len(res.get_candidates("a2")) == 1
    # Both sources retrieve the same target candidate
    assert res.get_candidates("a1")[0].target_id == "b1"
    assert res.get_candidates("a2")[0].target_id == "b1"
