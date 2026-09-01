"""CLI entry point for the Hybrid Semantic PDF Comparison Engine."""

import sys
import argparse
from pdf_comparator.core.engine import ComparisonEngine
from pdf_comparator.core.models import MatchStatus
from pdf_comparator.ingestion.extractor import PDFExtractionError


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

        sec = res.stats.processing_time_ms / 1000.0

        print("\nPDF Comparison Complete\n")
        print(f"Source: {res.source_document}")
        print(f"Target: {res.target_document}\n")
        print(f"Pages processed: {res.stats.pages_processed}")
        print(f"Chunks extracted: {res.stats.chunks_extracted}")
        print(f"Exact matches: {res.stats.exact_matches}")
        print(f"Semantic alignments: {res.stats.semantic_matches}")
        print(f"Unchanged: {unchanged_cnt}")
        print(f"Modified: {modified_cnt}")
        print(f"Added: {added_cnt}")
        print(f"Removed: {removed_cnt}\n")
        print(f"Processing time: {sec:.2f}s\n")

    except PDFExtractionError as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
