"""Comparison, alignment, and structural analysis module."""

from pdf_comparator.comparison.alignment import (
    AlignedPair,
    AlignmentResult,
    CandidateAligner,
    calculate_lexical_similarity,
    calculate_numeric_entity_similarity,
    calculate_positional_similarity,
    calculate_section_similarity,
    calculate_type_compatibility,
)
from pdf_comparator.comparison.exact import ExactMatcher, ExactMatchResult
from pdf_comparator.comparison.semantic import (
    CandidateMatch,
    SemanticRetrievalResult,
    SemanticRetriever,
)

__all__ = [
    "ExactMatcher",
    "ExactMatchResult",
    "CandidateMatch",
    "SemanticRetrievalResult",
    "SemanticRetriever",
    "CandidateAligner",
    "AlignedPair",
    "AlignmentResult",
    "calculate_lexical_similarity",
    "calculate_section_similarity",
    "calculate_type_compatibility",
    "calculate_numeric_entity_similarity",
    "calculate_positional_similarity",
]
