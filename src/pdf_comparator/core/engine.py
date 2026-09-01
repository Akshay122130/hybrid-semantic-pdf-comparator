"""Main pipeline orchestrator for the Hybrid Semantic PDF Comparison Engine."""

import os
import time
from datetime import datetime, timezone
from typing import List, Optional

from pdf_comparator.comparison.alignment import AlignmentResult, CandidateAligner
from pdf_comparator.comparison.exact import ExactMatcher, ExactMatchResult
from pdf_comparator.comparison.semantic import SemanticRetrievalResult, SemanticRetriever
from pdf_comparator.comparison.structural import StructuralAnalyzer
from pdf_comparator.core.models import (
    Chunk,
    ComparisonResult,
    MatchResult,
    MatchStatus,
    ProcessingStats,
    SeverityLevel,
)
from pdf_comparator.ingestion.extractor import PDFExtractionError, PDFExtractor
from pdf_comparator.processing.segmenter import DocumentSegmenter
from pdf_comparator.scoring.classifier import ResultClassifier


class ComparisonEngine:
    """End-to-end pipeline orchestrator for comparing two PDF documents.
    
    Pipeline Phases:
        1. PDF Extraction (PyMuPDF native extraction)
        2. Preprocessing & Segmentation (Paragraph + Sentence hierarchy)
        3. Deterministic Exact Matching (Hash-indexed O(N+M) matching)
        4. Semantic Candidate Retrieval (Sentence Transformers + FAISS vector indexing)
        5. Multi-Signal Alignment (Semantic, Lexical, Section, Entity, Type, Positional)
        6. Content-Aware Structural Analysis (Numbers, Dates, Currencies, Durations, Modalities)
        7. Final Classification & Scoring (MatchStatus, SeverityLevel, Confidence)
    """

    def __init__(
        self,
        extractor: Optional[PDFExtractor] = None,
        segmenter: Optional[DocumentSegmenter] = None,
        exact_matcher: Optional[ExactMatcher] = None,
        semantic_retriever: Optional[SemanticRetriever] = None,
        candidate_aligner: Optional[CandidateAligner] = None,
        structural_analyzer: Optional[StructuralAnalyzer] = None,
        result_classifier: Optional[ResultClassifier] = None,
    ):
        """Initialize the comparison engine with reusable pipeline components."""
        self.extractor = extractor or PDFExtractor()
        self.segmenter = segmenter or DocumentSegmenter()
        self.exact_matcher = exact_matcher or ExactMatcher()
        self.semantic_retriever = semantic_retriever or SemanticRetriever()
        self.candidate_aligner = candidate_aligner or CandidateAligner()
        self.structural_analyzer = structural_analyzer or StructuralAnalyzer()
        self.result_classifier = result_classifier or ResultClassifier(
            structural_analyzer=self.structural_analyzer
        )

    def _sort_results(self, results: List[MatchResult]) -> List[MatchResult]:
        """Deterministically sort final MatchResult objects by page and position ordering."""
        def sort_key(res: MatchResult):
            if res.source_chunk:
                p_src = res.source_chunk.page_num
                id_src = res.source_chunk.id
            else:
                p_src = 99999
                id_src = "ZZZ"

            if res.target_chunk:
                p_tgt = res.target_chunk.page_num
                id_tgt = res.target_chunk.id
            else:
                p_tgt = 99999
                id_tgt = "ZZZ"

            return (p_src, id_src, p_tgt, id_tgt, res.status.value)

        return sorted(results, key=sort_key)

    def compare(
        self,
        source_path: str,
        target_path: str,
        top_k: int = 5,
        min_alignment_score: float = 0.45,
    ) -> ComparisonResult:
        """Execute end-to-end comparison between two PDF documents.

        Args:
            source_path: File path to Source Document A.
            target_path: File path to Target Document B.
            top_k: Top-K candidates to retrieve per unmatched chunk in Phase 5.
            min_alignment_score: Minimum composite score required for Phase 6 alignment.

        Returns:
            ComparisonResult containing matched results, processing statistics, and metadata.
        """
        start_time = time.monotonic()
        timestamp_str = datetime.now(timezone.utc).isoformat()

        # Validate file paths
        if not os.path.exists(source_path):
            raise PDFExtractionError(f"Source file path does not exist: {source_path}")
        if not os.path.exists(target_path):
            raise PDFExtractionError(f"Target file path does not exist: {target_path}")

        # 1. Native PDF Ingestion
        try:
            raw_doc_a = self.extractor.extract(source_path)
            raw_doc_b = self.extractor.extract(target_path)
        except PDFExtractionError:
            raise
        except Exception as e:
            raise PDFExtractionError(f"Failed to extract PDF document: {str(e)}") from e

        # 2. Preprocessing & Segmentation
        chunks_a = self.segmenter.segment(raw_doc_a)
        chunks_b = self.segmenter.segment(raw_doc_b)

        # 3. Deterministic Exact Matching
        exact_res: ExactMatchResult = self.exact_matcher.match(chunks_a, chunks_b)

        # 4. Semantic Candidate Retrieval (Phase 5)
        if exact_res.unmatched_chunks_a and exact_res.unmatched_chunks_b:
            retrieval_res: SemanticRetrievalResult = self.semantic_retriever.retrieve_candidates(
                exact_res.unmatched_chunks_a,
                exact_res.unmatched_chunks_b,
                top_k=top_k,
            )
        else:
            retrieval_res = SemanticRetrievalResult(candidates_by_source={})

        # 5. Multi-Signal Candidate Alignment (Phase 6)
        if exact_res.unmatched_chunks_a and exact_res.unmatched_chunks_b:
            alignment_res: AlignmentResult = self.candidate_aligner.align(
                retrieval_res,
                exact_res.unmatched_chunks_a,
                exact_res.unmatched_chunks_b,
                min_alignment_score=min_alignment_score,
            )
        else:
            alignment_res = AlignmentResult(
                aligned_pairs=[],
                unaligned_chunks_a=list(exact_res.unmatched_chunks_a),
                unaligned_chunks_b=list(exact_res.unmatched_chunks_b),
            )

        # 6 & 7. Content-Aware Structural Analysis (Phase 7) & Final Classification (Phase 8)
        final_match_results = self.result_classifier.classify(
            exact_res, alignment_res, retrieval_res
        )

        # Deterministic Result Ordering
        sorted_results = self._sort_results(final_match_results)

        # Calculate statistics
        elapsed_ms = (time.monotonic() - start_time) * 1000.0

        exact_count = len(exact_res.matched_results)
        semantic_count = len(alignment_res.aligned_pairs)
        added_count = len(alignment_res.unaligned_chunks_b)
        removed_count = len(alignment_res.unaligned_chunks_a)

        stats = ProcessingStats(
            pages_processed=raw_doc_a.total_pages + raw_doc_b.total_pages,
            chunks_extracted=len(chunks_a) + len(chunks_b),

            exact_matches=exact_count,
            semantic_matches=semantic_count,
            added=added_count,
            removed=removed_count,
            ocr_pages=0,
            tables_detected=0,
            processing_time_ms=round(elapsed_ms, 2),
        )

        return ComparisonResult(
            source_document=os.path.basename(source_path),
            target_document=os.path.basename(target_path),
            results=sorted_results,
            stats=stats,
            timestamp=timestamp_str,
            engine_version="1.0.0",
        )
