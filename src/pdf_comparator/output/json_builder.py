"""JSON report builder for document comparison results."""

import json
from pathlib import Path
from typing import Any, Dict, Union
from pdf_comparator.core.models import ComparisonResult, MatchStatus, SeverityLevel


class JSONReportBuilder:
    """Builds machine-readable JSON reports from ComparisonResult objects."""

    def calculate_summary(self, result: ComparisonResult) -> Dict[str, int]:
        """Compute status and severity counts from results."""
        summary = {
            "unchanged": 0,
            "modified": 0,
            "added": 0,
            "removed": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "none": 0,
        }

        for match in result.results:
            if match.status == MatchStatus.UNCHANGED:
                summary["unchanged"] += 1
            elif match.status == MatchStatus.MODIFIED:
                summary["modified"] += 1
            elif match.status == MatchStatus.ADDED:
                summary["added"] += 1
            elif match.status == MatchStatus.REMOVED:
                summary["removed"] += 1

            if match.severity == SeverityLevel.HIGH:
                summary["high"] += 1
            elif match.severity == SeverityLevel.MEDIUM:
                summary["medium"] += 1
            elif match.severity == SeverityLevel.LOW:
                summary["low"] += 1
            elif match.severity == SeverityLevel.NONE:
                summary["none"] += 1

        return summary

    def build_dict(self, result: ComparisonResult) -> Dict[str, Any]:
        """Convert ComparisonResult into a clean report dictionary."""
        summary = self.calculate_summary(result)
        res_dict = result.to_dict()

        return {
            "source_document": res_dict["source_document"],
            "target_document": res_dict["target_document"],
            "timestamp": res_dict.get("timestamp", ""),
            "engine_version": res_dict.get("engine_version", "1.0.0"),
            "summary": summary,
            "processing_stats": res_dict["stats"],
            "results": res_dict["results"],
        }

    def build(self, result: ComparisonResult, indent: int = 2) -> str:
        """Serialize ComparisonResult into a formatted JSON string.

        Args:
            result: ComparisonResult object.
            indent: Indentation level for readable JSON formatting.

        Returns:
            JSON formatted string.
        """
        data = self.build_dict(result)
        return json.dumps(data, indent=indent, ensure_ascii=False)

    def write(self, result: ComparisonResult, output_path: Union[str, Path], indent: int = 2) -> Path:
        """Write JSON report to disk.

        Args:
            result: ComparisonResult object.
            output_path: File path to save JSON output.
            indent: Indentation level.

        Returns:
            Path object pointing to the created JSON file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = self.build(result, indent=indent)
        path.write_text(content, encoding="utf-8")
        return path
