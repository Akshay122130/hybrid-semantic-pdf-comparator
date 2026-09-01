"""Deterministic content-aware structural change detection for aligned chunk pairs."""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Set


class StructuralChangeType(str, Enum):
    """Types of detected deterministic structural changes."""
    NUMBER_CHANGE = "number_change"
    CURRENCY_CHANGE = "currency_change"
    PERCENTAGE_CHANGE = "percentage_change"
    DATE_CHANGE = "date_change"
    DURATION_CHANGE = "duration_change"
    UNIT_CHANGE = "unit_change"
    MODALITY_CHANGE = "modality_change"
    ENTITY_ADDED = "entity_added"
    ENTITY_REMOVED = "entity_removed"


@dataclass
class StructuralChange:
    """Individual structural change detected between source and target text."""
    change_type: StructuralChangeType
    old_value: Optional[str]
    new_value: Optional[str]
    source_chunk_id: str
    target_chunk_id: str
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_type": self.change_type.value,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "source_chunk_id": self.source_chunk_id,
            "target_chunk_id": self.target_chunk_id,
            "explanation": self.explanation,
        }


@dataclass
class StructuralChangeResult:
    """Collection of structural changes detected for an aligned chunk pair."""
    source_chunk_id: str
    target_chunk_id: str
    changes: List[StructuralChange] = field(default_factory=list)
    has_structural_changes: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_chunk_id": self.source_chunk_id,
            "target_chunk_id": self.target_chunk_id,
            "changes": [c.to_dict() for c in self.changes],
            "has_structural_changes": self.has_structural_changes,
        }


# Written numbers to digit conversion mapping
NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "forty-five": 45, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100,
    "one hundred": 100, "two years": 2, "three years": 3, "five years": 5,
}

MODALITY_TERMS = {
    "must", "shall", "may", "should", "required",
    "prohibited", "cannot", "permitted", "will"
}

MONTHS_MAP = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sept": 9, "sep": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12
}


def parse_number_value(val_str: str) -> Optional[float]:
    """Parse string or word into a float numeric value."""
    s = val_str.strip().lower()
    if s in NUMBER_WORDS:
        return float(NUMBER_WORDS[s])
    clean = s.replace(",", "")
    try:
        return float(clean)
    except ValueError:
        return None


# Regular expressions for entity extraction
CURRENCY_RE = re.compile(
    r"(?P<curr_prefix>\$|\€|\£|\₹|USD|EUR|INR|GBP)\s*(?P<amount_prefix>[\d,]+(?:\.\d+)?)\b"
    r"|\b(?P<amount_suffix>[\d,]+(?:\.\d+)?)\s*(?P<curr_suffix>USD|EUR|INR|GBP)\b"
)

PERCENTAGE_RE = re.compile(
    r"\b(?P<val>[\d,]+(?:\.\d+)?|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|fifty)\b)\s*(?P<unit>\%|percent\b)",
    re.IGNORECASE,
)


DURATION_RE = re.compile(
    r"\b(?P<val>\d+|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|thirty|forty-five|forty|fifty|sixty)\b)\s+(?P<unit>days?|weeks?|months?|years?|hours?|minutes?)\b",
    re.IGNORECASE,
)

UNIT_RE = re.compile(
    r"\b(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>kg|g|km|m|MB|GB)\b"
)

DATE_RE = re.compile(
    r"\b(?P<d1>\d{4}-\d{2}-\d{2})\b"
    r"|\b(?P<d2>\d{1,2})[/\-](?P<m2>\d{1,2})[/\-](?P<y2>\d{4})\b"
    r"|\b(?P<d3>\d{1,2})(?:st|nd|rd|th)?\s+(?P<m3>January|Feb|March|April|May|June|July|August|Sept|September|Oct|October|Nov|November|Dec|December)\s+(?P<y3>\d{4})\b"
    r"|\b(?P<m4>January|Feb|March|April|May|June|July|August|Sept|September|Oct|October|Nov|November|Dec|December)\s+(?P<d4>\d{1,2})(?:st|nd|rd|th)?,?\s+(?P<y4>\d{4})\b",
    re.IGNORECASE,
)


def extract_dates(text: str) -> List[Tuple[int, str, Tuple[int, int, int]]]:
    """Extract dates and return (position, raw_text, normalized_tuple(YYYY, MM, DD))."""
    results = []
    for m in DATE_RE.finditer(text):
        raw = m.group(0)
        pos = m.start()
        norm_date = None
        if m.group("d1"):
            parts = m.group("d1").split("-")
            norm_date = (int(parts[0]), int(parts[1]), int(parts[2]))
        elif m.group("d2"):
            norm_date = (int(m.group("y2")), int(m.group("m2")), int(m.group("d2")))
        elif m.group("d3"):
            month = MONTHS_MAP.get(m.group("m3").lower(), 1)
            norm_date = (int(m.group("y3")), month, int(m.group("d3")))
        elif m.group("m4"):
            month = MONTHS_MAP.get(m.group("m4").lower(), 1)
            norm_date = (int(m.group("y4")), month, int(m.group("d4")))
        if norm_date:
            results.append((pos, raw, norm_date))
    return results


def extract_currencies(text: str) -> List[Tuple[int, str, Tuple[str, float]]]:
    """Extract currency amounts and return (position, raw_text, normalized_tuple(code, amount))."""
    results = []
    for m in CURRENCY_RE.finditer(text):
        raw = m.group(0)
        pos = m.start()
        curr = m.group("curr_prefix") or m.group("curr_suffix")
        amt_str = m.group("amount_prefix") or m.group("amount_suffix")
        val = parse_number_value(amt_str)
        if val is not None and curr:
            curr_code = curr.upper()
            if curr_code == "$":
                curr_code = "USD"
            elif curr_code == "€":
                curr_code = "EUR"
            elif curr_code == "£":
                curr_code = "GBP"
            elif curr_code == "₹":
                curr_code = "INR"
            results.append((pos, raw, (curr_code, val)))
    return results


def extract_percentages(text: str) -> List[Tuple[int, str, float]]:
    """Extract percentages and return (position, raw_text, float_value)."""
    results = []
    for m in PERCENTAGE_RE.finditer(text):
        raw = m.group(0)
        pos = m.start()
        val = parse_number_value(m.group("val"))
        if val is not None:
            results.append((pos, raw, val))
    return results


def extract_durations(text: str) -> List[Tuple[int, str, Tuple[float, str]]]:
    """Extract durations and return (position, raw_text, normalized_tuple(count, unit_singular))."""
    results = []
    for m in DURATION_RE.finditer(text):
        raw = m.group(0)
        pos = m.start()
        val = parse_number_value(m.group("val"))
        unit = m.group("unit").lower().rstrip("s")
        if val is not None:
            results.append((pos, raw, (val, unit)))
    return results


def extract_units(text: str) -> List[Tuple[int, str, Tuple[float, str]]]:
    """Extract measurements with units and return (position, raw_text, normalized_tuple(val, unit))."""
    results = []
    for m in UNIT_RE.finditer(text):
        raw = m.group(0)
        pos = m.start()
        val = parse_number_value(m.group("val"))
        unit = m.group("unit")
        if val is not None:
            results.append((pos, raw, (val, unit)))
    return results


def extract_modalities(text: str) -> List[Tuple[int, str, str]]:
    """Extract obligation/modality terms and return (position, raw_text, normalized_term)."""
    results = []
    for m in re.finditer(r"\b([A-Za-z]+)\b", text.lower()):
        word = m.group(1)
        if word in MODALITY_TERMS:
            results.append((m.start(), text[m.start():m.end()], word))
    return results


def extract_standalone_numbers(
    text: str,
    ignore_positions: Set[int],
) -> List[Tuple[int, str, float]]:
    """Extract standalone numbers ignoring section/page metadata or numbers inside other entities."""
    results = []
    # Filter out "Section 1", "Page 3", list numbering "1."
    clean = re.sub(r"\b(section|page|chapter|article|appendix)\s+\d+\b", "", text, flags=re.IGNORECASE)
    clean = re.sub(r"^\d+\.\s+", "", clean)

    for m in re.finditer(r"\b\d+(?:\.\d+)?\b", clean):
        pos = m.start()
        if pos in ignore_positions:
            continue
        val = parse_number_value(m.group(0))
        if val is not None:
            results.append((pos, m.group(0), val))
    return results


class StructuralAnalyzer:
    """Analyzes aligned chunk pairs to detect deterministic content changes in structured entities.
    
    Architectural Boundary:
        Phase 7 IDENTIFIES structural changes only. It does NOT decide final severity,
        confidence, or business classification (MODIFIED/ADDED/REMOVED). Those are reserved
        for Phase 8 synthesis.
    """

    def analyze_pair(
        self,
        source_chunk: Optional[Any],
        target_chunk: Optional[Any],
        source_id: str = "",
        target_id: str = "",
    ) -> StructuralChangeResult:
        """Analyze aligned source and target text for structured entity changes.

        Args:
            source_chunk: Source Chunk object from Document A (or None).
            target_chunk: Target Chunk object from Document B (or None).
            source_id: Source chunk identifier.
            target_id: Target chunk identifier.

        Returns:
            StructuralChangeResult containing a list of detected StructuralChange instances.
        """
        src_id = source_chunk.id if source_chunk else source_id
        tgt_id = target_chunk.id if target_chunk else target_id

        src_text = source_chunk.original_text if source_chunk else ""
        tgt_text = target_chunk.original_text if target_chunk else ""

        changes: List[StructuralChange] = []

        if not src_text and not tgt_text:
            return StructuralChangeResult(src_id, tgt_id, [], False)

        # 1. Modality / Obligation changes
        mod_src = extract_modalities(src_text)
        mod_tgt = extract_modalities(tgt_text)
        if mod_src and mod_tgt:
            if mod_src[0][2] != mod_tgt[0][2]:
                changes.append(
                    StructuralChange(
                        change_type=StructuralChangeType.MODALITY_CHANGE,
                        old_value=mod_src[0][1],
                        new_value=mod_tgt[0][1],
                        source_chunk_id=src_id,
                        target_chunk_id=tgt_id,
                        explanation=f"Modality term changed from '{mod_src[0][1]}' to '{mod_tgt[0][1]}'.",
                    )
                )

        # 2. Currency changes
        curr_src = extract_currencies(src_text)
        curr_tgt = extract_currencies(tgt_text)
        if curr_src and curr_tgt:
            # Check if canonical currency code or numeric value changed
            if curr_src[0][2] != curr_tgt[0][2]:
                changes.append(
                    StructuralChange(
                        change_type=StructuralChangeType.CURRENCY_CHANGE,
                        old_value=curr_src[0][1],
                        new_value=curr_tgt[0][1],
                        source_chunk_id=src_id,
                        target_chunk_id=tgt_id,
                        explanation=f"Currency amount changed from '{curr_src[0][1]}' to '{curr_tgt[0][1]}'.",
                    )
                )

        # 3. Date changes
        date_src = extract_dates(src_text)
        date_tgt = extract_dates(tgt_text)
        if date_src and date_tgt:
            if date_src[0][2] != date_tgt[0][2]:
                changes.append(
                    StructuralChange(
                        change_type=StructuralChangeType.DATE_CHANGE,
                        old_value=date_src[0][1],
                        new_value=date_tgt[0][1],
                        source_chunk_id=src_id,
                        target_chunk_id=tgt_id,
                        explanation=f"Date changed from '{date_src[0][1]}' to '{date_tgt[0][1]}'.",
                    )
                )

        # 4. Duration changes
        dur_src = extract_durations(src_text)
        dur_tgt = extract_durations(tgt_text)
        if dur_src and dur_tgt:
            if dur_src[0][2] != dur_tgt[0][2]:
                changes.append(
                    StructuralChange(
                        change_type=StructuralChangeType.DURATION_CHANGE,
                        old_value=dur_src[0][1],
                        new_value=dur_tgt[0][1],
                        source_chunk_id=src_id,
                        target_chunk_id=tgt_id,
                        explanation=f"Duration changed from '{dur_src[0][1]}' to '{dur_tgt[0][1]}'.",
                    )
                )

        # 5. Percentage changes
        pct_src = extract_percentages(src_text)
        pct_tgt = extract_percentages(tgt_text)
        if pct_src and pct_tgt:
            if pct_src[0][2] != pct_tgt[0][2]:
                changes.append(
                    StructuralChange(
                        change_type=StructuralChangeType.PERCENTAGE_CHANGE,
                        old_value=pct_src[0][1],
                        new_value=pct_tgt[0][1],
                        source_chunk_id=src_id,
                        target_chunk_id=tgt_id,
                        explanation=f"Percentage value changed from '{pct_src[0][1]}' to '{pct_tgt[0][1]}'.",
                    )
                )

        # 6. Unit changes
        unit_src = extract_units(src_text)
        unit_tgt = extract_units(tgt_text)
        if unit_src and unit_tgt:
            if unit_src[0][2] != unit_tgt[0][2]:
                changes.append(
                    StructuralChange(
                        change_type=StructuralChangeType.UNIT_CHANGE,
                        old_value=unit_src[0][1],
                        new_value=unit_tgt[0][1],
                        source_chunk_id=src_id,
                        target_chunk_id=tgt_id,
                        explanation=f"Measurement/unit changed from '{unit_src[0][1]}' to '{unit_tgt[0][1]}'.",
                    )
                )

        # 7. Standalone number changes (only if not covered by duration/currency/date/percentage/unit)
        if not (curr_src or date_src or dur_src or pct_src or unit_src):
            num_src = extract_standalone_numbers(src_text, set())
            num_tgt = extract_standalone_numbers(tgt_text, set())
            if num_src and num_tgt:
                if num_src[0][2] != num_tgt[0][2]:
                    changes.append(
                        StructuralChange(
                            change_type=StructuralChangeType.NUMBER_CHANGE,
                            old_value=num_src[0][1],
                            new_value=num_tgt[0][1],
                            source_chunk_id=src_id,
                            target_chunk_id=tgt_id,
                            explanation=f"Numerical value changed from '{num_src[0][1]}' to '{num_tgt[0][1]}'.",
                        )
                    )

        # 8. Added / Removed entities check (e.g. Duration in source but missing in target)
        if dur_src and not dur_tgt:
            changes.append(
                StructuralChange(
                    change_type=StructuralChangeType.ENTITY_REMOVED,
                    old_value=dur_src[0][1],
                    new_value=None,
                    source_chunk_id=src_id,
                    target_chunk_id=tgt_id,
                    explanation=f"Duration entity '{dur_src[0][1]}' was removed.",
                )
            )
        elif not dur_src and dur_tgt:
            changes.append(
                StructuralChange(
                    change_type=StructuralChangeType.ENTITY_ADDED,
                    old_value=None,
                    new_value=dur_tgt[0][1],
                    source_chunk_id=src_id,
                    target_chunk_id=tgt_id,
                    explanation=f"Duration entity '{dur_tgt[0][1]}' was added.",
                )
            )

        return StructuralChangeResult(
            source_chunk_id=src_id,
            target_chunk_id=tgt_id,
            changes=changes,
            has_structural_changes=len(changes) > 0,
        )
