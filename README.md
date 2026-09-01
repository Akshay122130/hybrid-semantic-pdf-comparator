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

- [x] **Phase 5: Semantic Embedding & Candidate Retrieval**
  - Lightweight local embeddings using `all-MiniLM-L6-v2` via `sentence-transformers`
  - FAISS inner-product vector indexing (`faiss.IndexFlatIP`) for fast top-k candidate retrieval
  - L2 normalization guaranteeing vector inner product equals cosine similarity
  - Candidate retrieval isolated from alignment to prevent premature false-positive matches
  - Unit tests covering paraphrase similarity, top-k filtering, metadata preservation, and score range boundaries

- [x] **Phase 6: Multi-Signal Alignment & 1-to-1 Correspondence**
  - `CandidateAligner` combining semantic, lexical, section, numeric/entity, type, and positional signals (`src/pdf_comparator/comparison/alignment.py`)
  - Determines the best one-to-one correspondence between unresolved source and target chunks
  - Greedy descending composite-score 1-to-1 assignment algorithm with deterministic tie-breaking
  - Configurable minimum alignment threshold (`min_alignment_score`) preventing low-confidence matches
  - Human-readable explainable rationale generation for every assigned pair

- [x] **Phase 7: Content-Aware Structural Change Detection**
  - Deterministic entity extraction & normalization (`src/pdf_comparator/comparison/structural.py`)
  - Detects changes in numbers, decimals, currencies, dates, durations, units, and obligation modalities (`must`, `shall`, `may`)
  - Identifies added or removed structured entities within aligned chunk pairs
  - Eliminates false positives from formatting variations (e.g. `1 January 2026` vs `January 1, 2026`, `30 days` vs `thirty days`)
  - Unit tests covering all entity types, multiple changes per chunk, formatting equivalence, and serializable output

- [x] **Phase 8: Final Classification, Severity & Confidence Scoring**
  - `ResultClassifier` synthesizing evidence from exact matching, semantic alignment, and structural change analysis into `MatchResult` objects (`src/pdf_comparator/scoring/classifier.py`)
  - Configurable `SeverityEvaluator` (`src/pdf_comparator/scoring/severity.py`) assigning `NONE`, `LOW`, `MEDIUM`, or `HIGH` severity based on entity modification types (e.g. monetary values, percentages, modality obligations)
  - `ConfidenceEvaluator` (`src/pdf_comparator/scoring/confidence.py`) computing deterministic reliability scores (0.0 to 1.0) incorporating composite alignment strength, candidate top1-top2 score margins, and multi-signal agreement
  - Transparent human-readable explanations generated for every final match result
  - Unit tests covering status classification, severity grading, confidence margin scaling, and deterministic execution

- [ ] **Phase 9: Output Generation (HTML/JSON) & CLI** (Pending)
- [ ] **Phase 10: Evaluation & Ground-Truth Testing** (Pending)

## Phase Boundary Separation
- **Phase 6 (Alignment)**: Answers *"Which source chunk corresponds to which target chunk?"* Produces `AlignedPair` correspondences without deciding business change status, final severity, or confidence.
- **Phase 7 (Content Analysis)**: Answers *"What specific structured tokens changed between aligned chunks?"* Detects changes in numbers, dates, currencies, durations, obligations, and negations.
- **Phase 8 (Classification & Scoring)**: Answers *"What is the final status (MODIFIED/ADDED/REMOVED), severity (LOW/MEDIUM/HIGH), and confidence rating?"* Synthesizes alignment and structural evidence into `MatchResult` objects.

## Final Classification, Severity & Confidence Design
- **Deterministic Rules vs LLMs**: The classification and scoring layer relies entirely on deterministic rule sets and evidence synthesis rather than LLM calls. This guarantees 100% reproducible outcomes across runs.
- **Severity vs. Confidence Separation**:
  - **Severity**: Represents business impact or potential risk of a change (e.g., changing `$10,000` to `$12,000` or `must` to `may` is `HIGH` severity). *Note: Severity rules are PoC heuristics and do not constitute professional or legal advice.*
  - **Confidence**: Represents system reliability in its classification (e.g. an exact match has `1.0` confidence; an aligned pair with strong multi-signal agreement and a wide candidate score margin has high confidence ~`0.90`).
- **Candidate Score Margin Impact**: When multiple candidate matches are retrieved by FAISS in Phase 5, confidence incorporates the score gap ($\text{top}_1 - \text{top}_2$). A wide margin boosts confidence, while a tight margin penalizes confidence due to candidate ambiguity.


## Content-Aware Structural Change Detection Design
- **Why Structural Analysis Follows Semantic Alignment**: Semantic embeddings group semantically related sentences together regardless of entity value diffs. Once Phase 6 establishes 1-to-1 correspondence, Phase 7 deterministically inspects the aligned pair for exact structured token modifications.
- **Normalized Entity Comparison**: Entity values are converted to canonical forms before comparison (e.g., dates normalized to `(YYYY, MM, DD)` tuples, currency strings normalized to `(code, float_val)` pairs, and written word numbers converted to numerical values). This avoids false changes triggered by trivial formatting differences.
- **Separation from Severity & Confidence**: Phase 7 exclusively reports facts (e.g., `DURATION_CHANGE`: `30 days` $\rightarrow$ `45 days`). It does not assign business risk (`HIGH` severity) or confidence scores; Phase 8 will weigh structural changes alongside semantic alignment scores to produce final classifications.


## Multi-Signal Alignment & 1-to-1 Correspondence Design
- **Why Semantic Similarity Alone Is Insufficient**: Embedding models measure stylistic and topical closeness. A sentence like *"Payment is due in 30 days"* and *"Payment is due in 45 days"* have near-identical vector embeddings (~0.90 similarity), but different contractual terms. Combining semantic similarity with token lexical overlap, section headers, numeric/entity overlap, and chunk type compatibility prevents false alignments.
- **One-to-One Assignment Algorithm**: A greedy descending composite-score algorithm evaluates all candidate pairs retrieved by Phase 5. Candidate pairs above `min_alignment_score` are sorted by composite score (with deterministic tie-breaking on semantic score, lexical score, page proximity, and chunk IDs). Each target chunk is assigned to at most one source chunk.
- **Explainability**: Every aligned pair generates a transparent explanation string outlining why the pair was selected (e.g. *"Selected candidate because of high semantic similarity, matching section context, compatible chunk types, and matching numeric/entity tokens"*).





