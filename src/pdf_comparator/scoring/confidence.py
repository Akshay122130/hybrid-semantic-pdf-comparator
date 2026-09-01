"""Deterministic confidence scoring model (Phase 8)."""

from typing import Optional
from pdf_comparator.comparison.alignment import AlignedPair
from pdf_comparator.core.models import MatchStatus


class ConfidenceEvaluator:
    """Evaluates classification confidence scores (0.0 to 1.0).
    
    Confidence represents reliability of the system decision, not severity or risk.
    """

    def evaluate_exact_confidence(self) -> float:
        """Confidence for exact hash-matched identical text."""
        return 1.0

    def evaluate_aligned_confidence(
        self,
        aligned_pair: AlignedPair,
        candidate_margin: Optional[float] = None,
    ) -> float:
        """Calculate confidence for an aligned pair using multi-signal evidence and candidate margin."""
        conf = aligned_pair.composite_score

        # Candidate margin adjustment (gap between 1st and 2nd top candidate)
        if candidate_margin is not None:
            if candidate_margin >= 0.20:
                conf += 0.05  # Strong separation boost
            elif candidate_margin < 0.05:
                conf -= 0.10  # Ambiguity penalty

        # Signal agreement boost (both semantic and lexical are strong)
        if aligned_pair.semantic_score >= 0.75 and aligned_pair.lexical_score >= 0.50:
            conf += 0.05

        return round(min(0.99, max(0.10, conf)), 4)

    def evaluate_unmatched_confidence(self) -> float:
        """Confidence for unmatched ADDED or REMOVED chunks after exhaustive alignment."""
        return 0.90

    def evaluate(
        self,
        status: MatchStatus,
        aligned_pair: Optional[AlignedPair] = None,
        candidate_margin: Optional[float] = None,
    ) -> float:
        """Main entry point to calculate confidence score."""
        if status == MatchStatus.UNCHANGED and aligned_pair is None:
            return self.evaluate_exact_confidence()

        if aligned_pair is not None:
            return self.evaluate_aligned_confidence(aligned_pair, candidate_margin)

        if status in (MatchStatus.ADDED, MatchStatus.REMOVED):
            return self.evaluate_unmatched_confidence()

        return 0.80
