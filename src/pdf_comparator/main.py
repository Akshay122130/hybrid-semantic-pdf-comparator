"""CLI entry point for the Hybrid Semantic PDF Comparison Engine."""

import sys
import argparse
from pathlib import Path
from pdf_comparator.core.engine import ComparisonEngine
from pdf_comparator.core.models import MatchStatus, SeverityLevel
from pdf_comparator.ingestion.extractor import PDFExtractionError
from pdf_comparator.output.html_builder import HTMLReportBuilder
from pdf_comparator.output.json_builder import JSONReportBuilder


def main() -> None:
    """CLI execution entry point."""
    parser = argparse.ArgumentParser(
        description="Hybrid Semantic PDF Comparison Engine - Compare PDF documents using exact matching and local AI embeddings."
    )
    parser.add_argument("source", help="Path to source PDF file (Document A)")
    parser.add_argument("target", help="Path to target PDF file (Document B)")
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.45,
        help="Minimum alignment score threshold (default: 0.45)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top-K candidates to retrieve per unmatched chunk (default: 5)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save HTML and JSON comparison reports (e.g. reports/)",
    )

    args = parser.parse_args()

    try:
        engine = ComparisonEngine()
        res = engine.compare(
            source_path=args.source,
            target_path=args.target,
            top_k=args.top_k,
            min_alignment_score=args.min_score,
        )

        modified_cnt = sum(1 for r in res.results if r.status == MatchStatus.MODIFIED)
        added_cnt = sum(1 for r in res.results if r.status == MatchStatus.ADDED)
        removed_cnt = sum(1 for r in res.results if r.status == MatchStatus.REMOVED)
        unchanged_cnt = sum(1 for r in res.results if r.status == MatchStatus.UNCHANGED)

        high_sev = sum(1 for r in res.results if r.severity == SeverityLevel.HIGH)
        med_sev = sum(1 for r in res.results if r.severity == SeverityLevel.MEDIUM)
        low_sev = sum(1 for r in res.results if r.severity == SeverityLevel.LOW)

        sec = res.stats.processing_time_ms / 1000.0

        print("\nPDF Comparison Complete\n")
        print(f"Source: {res.source_document}")
        print(f"Target: {res.target_document}\n")
        print(f"Unchanged: {unchanged_cnt}")
        print(f"Modified: {modified_cnt}")
        print(f"Added: {added_cnt}")
        print(f"Removed: {removed_cnt}\n")
        print(f"High severity: {high_sev}")
        print(f"Medium severity: {med_sev}")
        print(f"Low severity: {low_sev}\n")
        print(f"Processing time: {sec:.2f}s\n")

        if args.output_dir:
            out_dir = Path(args.output_dir)
            html_path = out_dir / "comparison_report.html"
            json_path = out_dir / "comparison_report.json"

            HTMLReportBuilder().write(res, html_path)
            JSONReportBuilder().write(res, json_path)

            print("Reports:")
            print(f"HTML: {html_path}")
            print(f"JSON: {json_path}\n")

    except PDFExtractionError as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
