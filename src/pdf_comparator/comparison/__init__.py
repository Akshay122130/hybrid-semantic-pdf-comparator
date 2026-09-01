"""Comparison, alignment, and structural analysis module."""

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
]
