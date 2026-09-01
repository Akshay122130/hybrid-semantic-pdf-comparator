# Hybrid Semantic PDF Comparison Engine

## Problem Statement
Document comparison tools often rely on rigid, purely deterministic character diffing or opaque, expensive LLM calls. The Hybrid Semantic PDF Comparison Engine addresses this gap by combining fast deterministic matching with local semantic embeddings and rule-based structural extraction. This engine accurately identifies unchanged, added, removed, and modified content across complex PDF documents—distinguishing trivial formatting edits from substantive changes (such as modifications to numbers, dates, obligations, or contractual terms) while providing human-readable explanations, severity scores, confidence levels, and rich visual output.

## Architecture Overview
The engine follows a modular, hybrid pipeline architecture designed for accuracy, speed, and explainability:

```text
PDF Ingestion (PyMuPDF / OCR Fallback / Table Structuring)
  └──> Preprocessing & Segmentation (Paragraph + Sentence Hierarchy)
        └──> Exact Matching (Hashing Normalized Text)
              └──> Candidate Retrieval (Sentence Transformers + FAISS)
                    └──> Multi-Signal Alignment (Semantic, Lexical, Entity, Positional)
                          └──> Content-Aware Analysis (Numbers, Dates, Obligations, Negations)
                                └──> Severity (LOW/MED/HIGH) & Confidence Scoring
                                      └──> Output Generation (Color-Coded HTML & JSON Export)
```

Key Architectural Principles:
- **Hybrid Paragraph + Sentence Hierarchy**: Paragraphs serve as positional alignment units while sentences enable fine-grained comparison.
- **Multi-Signal Candidate Alignment**: FAISS handles candidate retrieval; final correspondence is determined by combining semantic, lexical, structural, and positional scores.
- **Deterministic Content Analysis**: Detects critical modifications in numbers, dates, currencies, percentages, durations, obligations (must/should), and negations.
- **Explainability & Transparency**: Every match result includes a human-readable explanation, a severity rating (LOW/MEDIUM/HIGH), and a classification confidence score.
- **Unified Processing**: Tables are parsed into structured chunks that flow through the main comparison engine without requiring a secondary pipeline.

## Implementation Status
- [x] **Phase 1: Project Foundation & Data Models**
  - Modular project structure (`src/pdf_comparator`)
  - Core data models (`Chunk`, `MatchResult`, `ProcessingStats`, and domain enums)
  - Unit tests for data model serialization and integrity
  - Minimal package configuration (`pyproject.toml`)
- [x] **Phase 2: Native PDF Ingestion**
  - Native PDF text, bounding box, and metadata extraction (`src/pdf_comparator/ingestion/extractor.py`)
  - Intermediate dataclasses (`RawBlock`, `RawPage`, `RawDocument`) preserving raw untouched text
  - Error handling for missing, invalid, corrupt, or empty PDFs (`PDFExtractionError`)
  - Unit tests using synthetic single-page, multi-page, empty, and corrupt PDFs

- [x] **Phase 3: Preprocessing & Document Segmentation**
  - Text normalization, line-break merging, and safe de-hyphenation (`src/pdf_comparator/processing/cleaner.py`)
  - Paragraph & sentence segmentation preserving `paragraph_id` and document hierarchy (`src/pdf_comparator/processing/segmenter.py`)
  - Section heading propagation and list item detection
  - Conversion of `RawDocument` into comparison-ready `Chunk` objects
  - Unit tests covering whitespace normalization, line wrapping, sentence splitting, headings, and bbox subdivision

- [x] **Phase 4: Deterministic Exact Matching**
  - Hash-indexed $O(N + M)$ exact matching engine (`src/pdf_comparator/comparison/exact.py`)
  - Duplicate handling using FIFO queue allocation per normalized key
  - Page-agnostic matching preserving reordering explanations
  - Generation of `ExactMatchResult` containing `UNCHANGED` `MatchResult` objects and unmatched candidate pools
  - Unit tests covering duplicates, reordering, empty documents, metadata preservation, and performance benchmark

- [ ] **Phase 5: Candidate Retrieval & Semantic Alignment** (Pending)
- [ ] **Phase 6: Content-Aware Analysis & Severity Scoring** (Pending)
- [ ] **Phase 7: Output Generation (HTML/JSON) & CLI** (Pending)
- [ ] **Phase 8: Evaluation & Ground-Truth Testing** (Pending)


