"""Comparison, alignment, and structural change analysis module."""

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
from pdf_comparator.comparison.structural import (
    StructuralAnalyzer,
    StructuralChange,
    StructuralChangeResult,
    StructuralChangeType,
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
    "StructuralAnalyzer",
    "StructuralChange",
    "StructuralChangeResult",
    "StructuralChangeType",
    "calculate_lexical_similarity",
    "calculate_section_similarity",
    "calculate_type_compatibility",
    "calculate_numeric_entity_similarity",
    "calculate_positional_similarity",
]
