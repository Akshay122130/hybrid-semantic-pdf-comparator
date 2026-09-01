"""Deterministic severity scoring model (Phase 8)."""

from typing import List, Optional
from pdf_comparator.comparison.structural import (
    StructuralChange,
    StructuralChangeResult,
    StructuralChangeType,
)
from pdf_comparator.core.models import Chunk, MatchStatus, SeverityLevel


class SeverityEvaluator:
    """Evaluates potential risk/impact severity for matched or unmatched document content.
    
    Severity Rules:
        - NONE: No meaningful change (UNCHANGED or normalized equivalent).
        - LOW: Minor wording change or non-critical added/removed text.
        - MEDIUM: Standard numeric, date, duration, unit change, or entity addition/removal.
        - HIGH: Critical currency changes, percentage shifts, or obligation modality shifts
          (must -> may, shall -> should, required -> permitted, permitted -> prohibited).
    """

    def evaluate_modified_severity(self, struct_result: StructuralChangeResult) -> SeverityLevel:
        """Determine severity for an aligned MODIFIED chunk pair based on structural changes."""
        if not struct_result.has_structural_changes:
            return SeverityLevel.LOW  # Pure textual wording modification

        highest_severity = SeverityLevel.LOW

        for change in struct_result.changes:
            c_type = change.change_type

            # High severity candidates
            if c_type in (
                StructuralChangeType.MODALITY_CHANGE,
                StructuralChangeType.CURRENCY_CHANGE,
                StructuralChangeType.PERCENTAGE_CHANGE,
            ):
                return SeverityLevel.HIGH

            # Medium severity candidates
            elif c_type in (
                StructuralChangeType.DATE_CHANGE,
                StructuralChangeType.DURATION_CHANGE,
                StructuralChangeType.NUMBER_CHANGE,
                StructuralChangeType.UNIT_CHANGE,
                StructuralChangeType.ENTITY_ADDED,
                StructuralChangeType.ENTITY_REMOVED,
            ):
                highest_severity = SeverityLevel.MEDIUM

        return highest_severity

    def evaluate_unmatched_severity(self, chunk: Chunk) -> SeverityLevel:
        """Determine severity for an ADDED or REMOVED chunk."""
        text = chunk.original_text.lower()

        # Check for high impact keywords (monetary, percentage, mandatory obligations)
        high_impact_terms = {"$", "usd", "eur", "gbp", "inr", "%", "percent", "must", "shall", "prohibited"}
        if any(term in text for term in high_impact_terms):
            return SeverityLevel.HIGH

        # Check for medium impact terms (dates, numbers, durations)
        medium_impact_terms = {"days", "months", "years", "due", "required", "payment", "fee"}
        if any(term in text for term in medium_impact_terms):
            return SeverityLevel.MEDIUM

        return SeverityLevel.LOW

    def evaluate(
        self,
        status: MatchStatus,
        struct_result: Optional[StructuralChangeResult] = None,
        chunk: Optional[Chunk] = None,
    ) -> SeverityLevel:
        """Main entry point to compute SeverityLevel."""
        if status == MatchStatus.UNCHANGED:
            return SeverityLevel.NONE

        if status == MatchStatus.MODIFIED:
            if struct_result:
                return self.evaluate_modified_severity(struct_result)
            return SeverityLevel.LOW

        if status in (MatchStatus.ADDED, MatchStatus.REMOVED):
            if chunk:
                return self.evaluate_unmatched_severity(chunk)
            return SeverityLevel.MEDIUM

        return SeverityLevel.LOW
