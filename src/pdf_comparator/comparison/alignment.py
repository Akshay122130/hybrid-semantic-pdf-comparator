"""Multi-signal candidate alignment and 1-to-1 correspondence matching."""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set

from pdf_comparator.comparison.semantic import CandidateMatch, SemanticRetrievalResult
from pdf_comparator.core.models import Chunk


# Extraction regex for structured tokens: numbers, percentages, dates (YYYY-MM-DD), currencies ($/€/£)
NUMERIC_ENTITY_RE = re.compile(r"\b(?:\$[\d,]+|\€[\d,]+|\£[\d,]+|\d+(?:\.\d+)?\%|\d{4}-\d{2}-\d{2}|\d+(?:\.\d+)?)\b")

# Token extraction regex for lexical similarity
TOKEN_RE = re.compile(r"\b\w+\b")

DEFAULT_WEIGHTS = {
    "semantic": 0.45,       # Semantic embedding similarity (primary signal)
    "lexical": 0.20,        # Token overlap / exact term match
    "section": 0.15,        # Section header alignment
    "numeric_entity": 0.10, # Number and structured token overlap
    "type_compat": 0.05,    # Chunk type matching (HEADING vs TEXT)
    "positional": 0.05,     # Page proximity boost
}


def calculate_lexical_similarity(text1: str, text2: str) -> float:
    """Calculate token-based Jaccard similarity between two strings."""
    tokens1 = set(TOKEN_RE.findall(text1.lower()))
    tokens2 = set(TOKEN_RE.findall(text2.lower()))
    if not tokens1 and not tokens2:
        return 0.0
    union = tokens1.union(tokens2)
    if not union:
        return 0.0
    return len(tokens1.intersection(tokens2)) / len(union)


def calculate_section_similarity(section1: str, section2: str) -> float:
    """Calculate section compatibility signal.
    
    Returns:
        1.0 if section headers match exactly.
        0.5 if section metadata is missing on either side (neutral).
        0.0 if sections explicitly conflict.
    """
    if section1 is None or section2 is None:
        return 0.5
    s1 = section1.strip().lower()
    s2 = section2.strip().lower()
    if s1 == s2:
        return 1.0
    return 0.0


def calculate_type_compatibility(type1: str, type2: str) -> float:
    """Calculate chunk type compatibility signal."""
    return 1.0 if type1 == type2 else 0.0


def calculate_numeric_entity_similarity(text1: str, text2: str) -> float:
    """Calculate overlap of structured numeric, date, percentage, and currency tokens."""
    nums1 = set(NUMERIC_ENTITY_RE.findall(text1))
    nums2 = set(NUMERIC_ENTITY_RE.findall(text2))
    
    if not nums1 and not nums2:
        return 0.5  # Neutral signal if neither sentence contains numeric tokens
    if not nums1 or not nums2:
        return 0.0  # Penalty if one sentence contains numbers and the other contains none
    
    union = nums1.union(nums2)
    return len(nums1.intersection(nums2)) / len(union)


def calculate_positional_similarity(page1: int, page2: int) -> float:
    """Calculate page proximity boost.
    
    Page proximity provides a minor positive signal but page distance does not block alignment.
    """
    distance = abs(page1 - page2)
    return max(0.0, 1.0 - 0.1 * distance)


@dataclass
class AlignedPair:
    """A resolved 1-to-1 correspondence pair between source and target chunks."""
    source_chunk: Chunk
    target_chunk: Chunk
    source_id: str
    target_id: str
    semantic_score: float
    lexical_score: float
    section_score: float
    type_score: float
    numeric_entity_score: float
    positional_score: float
    composite_score: float
    explanation: str


@dataclass
class AlignmentResult:
    """Output of the multi-signal alignment stage containing 1-to-1 pairs and unaligned pools."""
    aligned_pairs: List[AlignedPair] = field(default_factory=list)
    unaligned_chunks_a: List[Chunk] = field(default_factory=list)
    unaligned_chunks_b: List[Chunk] = field(default_factory=list)


class CandidateAligner:
    """Ranks semantic candidates using multi-signal scoring and enforces 1-to-1 alignment.
    
    Multi-Signal Scoring:
        Combines semantic similarity, token lexical overlap, section context, chunk type
        compatibility, numeric/entity overlap, and page proximity.
        
    One-to-One Alignment Assignment:
        Uses a greedy descending assignment algorithm. All candidate pairs are scored,
        filtered by minimum_alignment_score, sorted deterministically, and greedily assigned
        so that each target chunk is paired with at most one source chunk.
    """

    def __init__(self, weights: Dict[str, float] = None):
        """Initialize aligner with configurable signal weights."""
        self.weights = weights if weights is not None else dict(DEFAULT_WEIGHTS)
        # Normalize weights to sum to 1.0
        total_w = sum(self.weights.values())
        if total_w > 0:
            self.weights = {k: v / total_w for k, v in self.weights.items()}

    def compute_composite_score(
        self,
        source: Chunk,
        target: Chunk,
        semantic_sim: float,
    ) -> Dict[str, float]:
        """Compute multi-signal sub-scores and weighted composite alignment score."""
        lexical = calculate_lexical_similarity(source.normalized_text, target.normalized_text)
        section = calculate_section_similarity(source.section, target.section)
        type_compat = calculate_type_compatibility(source.type, target.type)
        numeric = calculate_numeric_entity_similarity(source.original_text, target.original_text)
        positional = calculate_positional_similarity(source.page_num, target.page_num)

        composite = (
            self.weights.get("semantic", 0.45) * semantic_sim
            + self.weights.get("lexical", 0.20) * lexical
            + self.weights.get("section", 0.15) * section
            + self.weights.get("numeric_entity", 0.10) * numeric
            + self.weights.get("type_compat", 0.05) * type_compat
            + self.weights.get("positional", 0.05) * positional
        )

        return {
            "semantic": semantic_sim,
            "lexical": lexical,
            "section": section,
            "type_compat": type_compat,
            "numeric_entity": numeric,
            "positional": positional,
            "composite": composite,
        }

    def generate_explanation(self, scores: Dict[str, float]) -> str:
        """Generate human-readable explanation for alignment choice based on signals."""
        reasons = []
        if scores["semantic"] >= 0.7:
            reasons.append("high semantic similarity")
        elif scores["semantic"] >= 0.5:
            reasons.append("moderate semantic similarity")

        if scores["lexical"] >= 0.5:
            reasons.append("strong lexical overlap")
        elif scores["lexical"] >= 0.3:
            reasons.append("partial lexical overlap")

        if scores["section"] == 1.0:
            reasons.append("matching section context")

        if scores["type_compat"] == 1.0:
            reasons.append("compatible chunk types")

        if scores["numeric_entity"] >= 0.5 and scores["numeric_entity"] != 0.5:
            reasons.append("matching numeric/entity tokens")

        if not reasons:
            return "Selected based on composite multi-signal score."

        return f"Selected candidate because of {', '.join(reasons)}."

    def align(
        self,
        retrieval_result: SemanticRetrievalResult,
        unmatched_a: List[Chunk],
        unmatched_b: List[Chunk],
        min_alignment_score: float = 0.45,
    ) -> AlignmentResult:
        """Perform 1-to-1 multi-signal candidate alignment.

        Args:
            retrieval_result: Phase 5 candidate retrieval result.
            unmatched_a: Unresolved source chunks from Document A.
            unmatched_b: Unresolved target chunks from Document B.
            min_alignment_score: Minimum composite score required to accept a pair.

        Returns:
            AlignmentResult with aligned 1-to-1 pairs and remaining unaligned pools.
        """
        if not unmatched_a or not unmatched_b:
            return AlignmentResult(
                aligned_pairs=[],
                unaligned_chunks_a=list(unmatched_a),
                unaligned_chunks_b=list(unmatched_b),
            )

        # Map chunks by ID for fast lookup
        map_a = {c.id: c for c in unmatched_a}
        map_b = {c.id: c for c in unmatched_b}

        # Build list of all candidate pairs across all source chunks
        candidate_pairs = []

        for source_id, candidate_list in retrieval_result.candidates_by_source.items():
            source_chunk = map_a.get(source_id)
            if not source_chunk:
                continue

            for candidate in candidate_list:
                target_chunk = map_b.get(candidate.target_id)
                if not target_chunk:
                    continue

                scores = self.compute_composite_score(
                    source_chunk, target_chunk, candidate.similarity_score
                )

                if scores["composite"] >= min_alignment_score:
                    explanation = self.generate_explanation(scores)
                    pair_item = {
                        "source_chunk": source_chunk,
                        "target_chunk": target_chunk,
                        "scores": scores,
                        "explanation": explanation,
                    }
                    candidate_pairs.append(pair_item)

        # Deterministic sorting for greedy 1-to-1 assignment:
        # Sort by (-composite_score, -semantic_score, -lexical_score, page_distance, source_id, target_id)
        candidate_pairs.sort(
            key=lambda item: (
                -item["scores"]["composite"],
                -item["scores"]["semantic"],
                -item["scores"]["lexical"],
                abs(item["source_chunk"].page_num - item["target_chunk"].page_num),
                item["source_chunk"].id,
                item["target_chunk"].id,
            )
        )

        assigned_sources: Set[str] = set()
        assigned_targets: Set[str] = set()
        aligned_pairs: List[AlignedPair] = []

        for item in candidate_pairs:
            src = item["source_chunk"]
            tgt = item["target_chunk"]

            if src.id not in assigned_sources and tgt.id not in assigned_targets:
                assigned_sources.add(src.id)
                assigned_targets.add(tgt.id)

                aligned_pair = AlignedPair(
                    source_chunk=src,
                    target_chunk=tgt,
                    source_id=src.id,
                    target_id=tgt.id,
                    semantic_score=item["scores"]["semantic"],
                    lexical_score=item["scores"]["lexical"],
                    section_score=item["scores"]["section"],
                    type_score=item["scores"]["type_compat"],
                    numeric_entity_score=item["scores"]["numeric_entity"],
                    positional_score=item["scores"]["positional"],
                    composite_score=item["scores"]["composite"],
                    explanation=item["explanation"],
                )
                aligned_pairs.append(aligned_pair)

        unaligned_a = [c for c in unmatched_a if c.id not in assigned_sources]
        unaligned_b = [c for c in unmatched_b if c.id not in assigned_targets]

        return AlignmentResult(
            aligned_pairs=aligned_pairs,
            unaligned_chunks_a=unaligned_a,
            unaligned_chunks_b=unaligned_b,
        )
