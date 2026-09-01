"""Performance benchmarking suite for measuring cold-start, warm execution, and per-phase latency (Phase 11)."""

import time
import pytest
import fitz
from pdf_comparator.comparison.alignment import CandidateAligner
from pdf_comparator.comparison.exact import ExactMatcher
from pdf_comparator.comparison.semantic import SemanticRetriever
from pdf_comparator.comparison.structural import StructuralAnalyzer
from pdf_comparator.core.engine import ComparisonEngine
from pdf_comparator.ingestion.extractor import PDFExtractor
from pdf_comparator.output.html_builder import HTMLReportBuilder
from pdf_comparator.output.json_builder import JSONReportBuilder
from pdf_comparator.processing.segmenter import DocumentSegmenter
from pdf_comparator.scoring.classifier import ResultClassifier


def generate_benchmark_pdf(path: str, num_pages: int, chunks_per_page: int) -> None:
    """Generate a synthetic PDF with predictable content for performance benchmarking."""
    doc = fitz.open()
    for p in range(num_pages):
        page = doc.new_page()
        y = 40
        for c in range(chunks_per_page):
            text = f"Page {p+1} Clause {c+1}: Supplier must deliver item {c*10} within {c+30} days for ${c*500+1000}."
            page.insert_text((40, y), text, fontsize=10)
            y += 20
    doc.save(path)
    doc.close()


def test_per_phase_performance_breakdown(tmp_path):
    """Benchmark per-phase processing latency on a synthetic 10-page document pair."""
    path_a = str(tmp_path / "bench_a.pdf")
    path_b = str(tmp_path / "bench_b.pdf")

    generate_benchmark_pdf(path_a, num_pages=10, chunks_per_page=15)
    generate_benchmark_pdf(path_b, num_pages=10, chunks_per_page=15)

    extractor = PDFExtractor()
    segmenter = DocumentSegmenter()
    exact_matcher = ExactMatcher()
    retriever = SemanticRetriever()
    aligner = CandidateAligner()
    analyzer = StructuralAnalyzer()
    classifier = ResultClassifier(structural_analyzer=analyzer)
    html_builder = HTMLReportBuilder()
    json_builder = JSONReportBuilder()

    # 1. Extraction
    t0 = time.perf_counter()
    raw_a = extractor.extract(path_a)
    raw_b = extractor.extract(path_b)
    t_extract = time.perf_counter() - t0

    # 2. Segmentation
    t0 = time.perf_counter()
    chunks_a = segmenter.segment(raw_a)
    chunks_b = segmenter.segment(raw_b)
    t_segment = time.perf_counter() - t0

    # 3. Exact Matching
    t0 = time.perf_counter()
    exact_res = exact_matcher.match(chunks_a, chunks_b)
    t_exact = time.perf_counter() - t0

    # 4. Semantic Retrieval
    t0 = time.perf_counter()
    retrieval_res = retriever.retrieve_candidates(exact_res.unmatched_chunks_a, exact_res.unmatched_chunks_b)
    t_semantic = time.perf_counter() - t0

    # 5. Alignment
    t0 = time.perf_counter()
    align_res = aligner.align(retrieval_res, exact_res.unmatched_chunks_a, exact_res.unmatched_chunks_b)
    t_align = time.perf_counter() - t0

    # 6. Classification & Structural Analysis
    t0 = time.perf_counter()
    match_results = classifier.classify(exact_res, align_res, retrieval_res)
    t_classify = time.perf_counter() - t0

    engine = ComparisonEngine(
        extractor=extractor,
        segmenter=segmenter,
        exact_matcher=exact_matcher,
        semantic_retriever=retriever,
        candidate_aligner=aligner,
        structural_analyzer=analyzer,
        result_classifier=classifier,
    )
    res = engine.compare(path_a, path_b)

    # 7. HTML & JSON Export
    t0 = time.perf_counter()
    _ = html_builder.build(res)
    t_html = time.perf_counter() - t0

    t0 = time.perf_counter()
    _ = json_builder.build(res)
    t_json = time.perf_counter() - t0

    print(f"\n--- PERFORMANCE BREAKDOWN (10 Pages, {len(chunks_a)+len(chunks_b)} Chunks) ---")
    print(f"1. PDF Extraction:       {t_extract*1000:.2f} ms")
    print(f"2. Document Segmenting:  {t_segment*1000:.2f} ms")
    print(f"3. Exact Matching:       {t_exact*1000:.2f} ms")
    print(f"4. FAISS Candidate Retrieval: {t_semantic*1000:.2f} ms")
    print(f"5. Multi-Signal Alignment:   {t_align*1000:.2f} ms")
    print(f"6. Classification & Struct:  {t_classify*1000:.2f} ms")
    print(f"7. HTML Generation:       {t_html*1000:.2f} ms")
    print(f"8. JSON Generation:       {t_json*1000:.2f} ms")

    assert len(match_results) > 0


def test_cold_start_vs_warm_benchmark(tmp_path):
    """Benchmark cold-start model initialization vs warm comparison execution latency."""
    path_a = str(tmp_path / "cold_a.pdf")
    path_b = str(tmp_path / "cold_b.pdf")

    generate_benchmark_pdf(path_a, num_pages=5, chunks_per_page=10)
    generate_benchmark_pdf(path_b, num_pages=5, chunks_per_page=10)

    # Cold Start (Model load + comparison)
    t0 = time.perf_counter()
    engine = ComparisonEngine()
    res_cold = engine.compare(path_a, path_b)
    t_cold = time.perf_counter() - t0

    # Warm Execution (Reusing existing engine instance)
    t0 = time.perf_counter()
    res_warm = engine.compare(path_a, path_b)
    t_warm = time.perf_counter() - t0

    print(f"\n--- COLD START VS WARM EXECUTION BENCHMARK ---")
    print(f"Cold-Start Latency (Includes Model Load): {t_cold:.3f} s")
    print(f"Warm Execution Latency (Reused Model):    {t_warm:.3f} s")

    assert res_cold.stats.chunks_extracted == res_warm.stats.chunks_extracted
