"""Deterministic exact text matching module for the Hybrid Semantic PDF Comparison Engine."""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List

from pdf_comparator.core.models import Chunk, MatchResult, MatchStatus, SeverityLevel


@dataclass
class ExactMatchResult:
    """Output structure of the exact matching pass.
    
    Contains paired UNCHANGED match results alongside unmatched chunk pools from Document A and B
    for downstream candidate retrieval and semantic alignment.
    """
    matched_results: List[MatchResult] = field(default_factory=list)
    unmatched_chunks_a: List[Chunk] = field(default_factory=list)
    unmatched_chunks_b: List[Chunk] = field(default_factory=list)


class ExactMatcher:
    """Deterministic hash-indexed exact matcher.
    
    Time Complexity:
        O(N + M) where N = len(chunks_a) and M = len(chunks_b).
        Indexing Document B takes O(M) time and O(M) space.
        Hash lookups for Document A chunks take O(1) average time, giving O(N) total.
    
    Duplicate Handling Strategy:
        Document B chunks are indexed by `normalized_text` into FIFO queues (deques).
        When a Document A chunk matches a normalized text key, the first available
        unconsumed Document B chunk is popped and paired (consumed exactly once).
        Any unconsumed Document B chunks remain in the unmatched pool for B.
    """

    def match(
        self,
        chunks_a: List[Chunk],
        chunks_b: List[Chunk],
    ) -> ExactMatchResult:
        """Perform exact text matching between Document A and Document B chunks.

        Args:
            chunks_a: List of Chunk objects from Document A (Base).
            chunks_b: List of Chunk objects from Document B (Target).

        Returns:
            ExactMatchResult containing UNCHANGED match results and remaining unmatched chunks.
        """
        if not chunks_a and not chunks_b:
            return ExactMatchResult([], [], [])
        if not chunks_a:
            return ExactMatchResult([], [], list(chunks_b))
        if not chunks_b:
            return ExactMatchResult([], list(chunks_a), [])

        # Index Document B chunks by normalized_text using a FIFO queue per key
        b_index: Dict[str, deque[Chunk]] = defaultdict(deque)
        for chunk_b in chunks_b:
            if chunk_b.normalized_text:
                b_index[chunk_b.normalized_text].append(chunk_b)

        matched_results: List[MatchResult] = []
        unmatched_a: List[Chunk] = []

        # Process Document A chunks in order
        for chunk_a in chunks_a:
            norm_key = chunk_a.normalized_text
            if norm_key and norm_key in b_index and len(b_index[norm_key]) > 0:
                chunk_b = b_index[norm_key].popleft()

                if chunk_a.page_num != chunk_b.page_num:
                    explanation = (
                        f"Exact text match (reordered from page {chunk_a.page_num} to page {chunk_b.page_num})."
                    )
                else:
                    explanation = "Exact text match."

                match_result = MatchResult(
                    status=MatchStatus.UNCHANGED,
                    source_chunk=chunk_a,
                    target_chunk=chunk_b,
                    similarity_score=1.0,
                    severity=SeverityLevel.NONE,
                    confidence=1.0,
                    explanation=explanation,
                )
                matched_results.append(match_result)
            else:
                unmatched_a.append(chunk_a)

        # Collect unconsumed Document B chunks maintaining original document order
        unmatched_b: List[Chunk] = []
        for chunk_b in chunks_b:
            norm_key = chunk_b.normalized_text
            if norm_key in b_index and chunk_b in b_index[norm_key]:
                unmatched_b.append(chunk_b)
                # Remove instance to handle duplicates in unconsumed check
                b_index[norm_key].remove(chunk_b)

        return ExactMatchResult(
            matched_results=matched_results,
            unmatched_chunks_a=unmatched_a,
            unmatched_chunks_b=unmatched_b,
        )
