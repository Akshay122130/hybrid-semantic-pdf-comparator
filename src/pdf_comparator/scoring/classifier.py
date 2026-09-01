"""Final classification and result synthesis module (Phase 8)."""

from typing import Dict, List, Optional
from pdf_comparator.comparison.alignment import AlignedPair, AlignmentResult
from pdf_comparator.comparison.exact import ExactMatchResult
from pdf_comparator.comparison.semantic import SemanticRetrievalResult
from pdf_comparator.comparison.structural import StructuralAnalyzer, StructuralChangeResult
from pdf_comparator.core.models import Chunk, MatchResult, MatchStatus, SeverityLevel
from pdf_comparator.scoring.confidence import ConfidenceEvaluator
from pdf_comparator.scoring.severity import SeverityEvaluator


class ResultClassifier:
    """Synthesizes evidence from exact matching, semantic alignment, and structural analysis
    into final MatchResult objects with status, severity, confidence, and explanations.
    """

    def __init__(
        self,
        severity_evaluator: Optional[SeverityEvaluator] = None,
        confidence_evaluator: Optional[ConfidenceEvaluator] = None,
        structural_analyzer: Optional[StructuralAnalyzer] = None,
    ):
        self.severity_evaluator = severity_evaluator or SeverityEvaluator()
        self.confidence_evaluator = confidence_evaluator or ConfidenceEvaluator()
        self.structural_analyzer = structural_analyzer or StructuralAnalyzer()

    def _get_candidate_margin(
        self,
        source_id: str,
        retrieval_result: Optional[SemanticRetrievalResult],
    ) -> Optional[float]:
        """Compute top1 - top2 similarity score margin from retrieval results."""
        if not retrieval_result:
            return None
        candidates = retrieval_result.get_candidates(source_id)
        if len(candidates) >= 2:
            return candidates[0].similarity_score - candidates[1].similarity_score
        return None

    def classify(
        self,
        exact_result: ExactMatchResult,
        alignment_result: AlignmentResult,
        retrieval_result: Optional[SemanticRetrievalResult] = None,
    ) -> List[MatchResult]:
        """Synthesize all phase evidence into final MatchResult instances.

        Args:
            exact_result: Phase 4 exact matching output.
            alignment_result: Phase 6 multi-signal alignment output.
            retrieval_result: Optional Phase 5 semantic retrieval output (for margin calculation).

        Returns:
            List of final MatchResult objects.
        """
        results: List[MatchResult] = []

        # 1. Exact matches from Phase 4
        for exact_match in exact_result.matched_results:
            match_res = MatchResult(
                status=MatchStatus.UNCHANGED,
                source_chunk=exact_match.source_chunk,
                target_chunk=exact_match.target_chunk,
                similarity_score=1.0,
                structural_changes={},
                severity=SeverityLevel.NONE,
                confidence=1.0,
                explanation="Exact normalized-text match; no content difference detected.",
            )
            results.append(match_res)

        # 2. Aligned pairs from Phase 6
        for pair in alignment_result.aligned_pairs:
            struct_res: StructuralChangeResult = self.structural_analyzer.analyze_pair(
                pair.source_chunk, pair.target_chunk
            )

            margin = self._get_candidate_margin(pair.source_id, retrieval_result)

            # Check if normalized texts are identical
            is_equivalent = (
                pair.source_chunk.normalized_text == pair.target_chunk.normalized_text
                and not struct_res.has_structural_changes
            )

            if is_equivalent:
                status = MatchStatus.UNCHANGED
                severity = SeverityLevel.NONE
                confidence = self.confidence_evaluator.evaluate(status, pair, margin)
                explanation = "Normalized-text equivalent match; formatting difference only."
            else:
                status = MatchStatus.MODIFIED
                severity = self.severity_evaluator.evaluate(status, struct_res)
                confidence = self.confidence_evaluator.evaluate(status, pair, margin)

                # Generate detailed explanation
                if struct_res.has_structural_changes:
                    change_desc = "; ".join(c.explanation for c in struct_res.changes)
                    explanation = f"Aligned chunks differ in content: {change_desc}"
                else:
                    explanation = f"Aligned chunks differ in wording ({pair.explanation.lower()})"

            match_res = MatchResult(
                status=status,
                source_chunk=pair.source_chunk,
                target_chunk=pair.target_chunk,
                similarity_score=pair.composite_score,
                structural_changes=struct_res.to_dict(),
                severity=severity,
                confidence=confidence,
                explanation=explanation,
            )
            results.append(match_res)

        # 3. Unmatched source chunks (REMOVED)
        for chunk_a in alignment_result.unaligned_chunks_a:
            severity = self.severity_evaluator.evaluate(MatchStatus.REMOVED, chunk=chunk_a)
            confidence = self.confidence_evaluator.evaluate(MatchStatus.REMOVED)
            match_res = MatchResult(
                status=MatchStatus.REMOVED,
                source_chunk=chunk_a,
                target_chunk=None,
                similarity_score=0.0,
                structural_changes={},
                severity=severity,
                confidence=confidence,
                explanation="Source chunk remained unmatched after exact and semantic alignment.",
            )
            results.append(match_res)

        # 4. Unmatched target chunks (ADDED)
        for chunk_b in alignment_result.unaligned_chunks_b:
            severity = self.severity_evaluator.evaluate(MatchStatus.ADDED, chunk=chunk_b)
            confidence = self.confidence_evaluator.evaluate(MatchStatus.ADDED)
            match_res = MatchResult(
                status=MatchStatus.ADDED,
                source_chunk=None,
                target_chunk=chunk_b,
                similarity_score=0.0,
                structural_changes={},
                severity=severity,
                confidence=confidence,
                explanation="Target chunk remained unmatched after exact and semantic alignment.",
            )
            results.append(match_res)

        return results
