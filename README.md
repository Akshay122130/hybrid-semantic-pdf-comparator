# Hybrid Semantic PDF Comparison Engine

## 1. Problem Statement
Traditional document comparison tools rely on rigid character-level diffing or opaque, expensive LLM calls. Character-based diffing fails when documents contain paraphrased sentences, reordered clauses, or minor formatting changes—generating noisy false-positive diffs. Conversely, LLMs introduce non-deterministic outputs, prompt injection risks, high API costs, latency, and potential data privacy concerns.

PDF documents present unique comparison challenges:
- **Paraphrased Clauses**: Expressing identical contractual intent using different vocabulary.
- **Reordered Sections**: Relocating paragraphs or sections across pages.
- **Substantive Content Shifts**: Modifications to critical entity values (numbers, currencies, percentages, dates, durations, or legal obligations).
- **Structural Modifications**: Insertion or deletion of clauses and subsections.

The **Hybrid Semantic PDF Comparison Engine** solves this problem by combining fast deterministic algorithms with local AI embeddings and rule-based structural extraction.

---

## 2. Solution Overview
The system follows a hybrid pipeline architecture guided by a core engineering principle:

> *"Use deterministic algorithms where exactness and explainability matter, and local semantic embeddings where semantic similarity is required."*

```text
Source PDF (A) ──┐
                 ├──► Native Ingestion (PyMuPDF)
Target PDF (B) ──┘          │
                            ▼
                     Preprocessing &
                      Segmentation
                            │
                            ▼
                      Exact Matching (Hash-Indexed O(N+M))
                            │
                            ▼
                     Semantic Candidate Retrieval
                     (SentenceTransformers + FAISS)
                            │
                            ▼
                     Multi-Signal Alignment
                     (Semantic, Lexical, Section, Entity, Positional)
                            │
                            ▼
                     Content-Aware Structural Analysis
                     (Currencies, Dates, Durations, Modalities)
                            │
                            ▼
                     Classification, Severity & Confidence Scoring
                            │
                            ▼
                      ComparisonResult
                         /        \
                        ▼          ▼
                      JSON        HTML
```

---

## 3. Why NOT an LLM?
The core comparison pipeline intentionally operates **without LLM generation dependencies**.

| Decision Factor | Local Deterministic + Embedding Pipeline | LLM-Based Comparison |
| :--- | :--- | :--- |
| **Determinism** | 100% reproducible across 5x+ repeated runs | Non-deterministic, temperature-dependent |
| **Privacy & Security** | 100% local, offline execution on CPU | Requires sending document text to cloud APIs |
| **Cost & Latency** | Free local execution; ~20ms warm latency | High token costs; several seconds per prompt |
| **Explainability** | Audit-traceable multi-signal breakdown | Opaque neural text generation |
| **Output Integrity** | Strict typing via dataclasses & JSON schema | Hallucination risks & schema breakdown |

*Note: An LLM could be added as an optional future post-processing layer for natural language executive summaries, but is not required for core comparison.*

---

## 4. Technology Stack
- **Core Language**: Python 3.10+
- **PDF Extraction**: [PyMuPDF](https://pymupdf.readthedocs.io/) (`fitz`)
- **Semantic Embeddings**: `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim)
- **Vector Candidate Indexing**: `faiss-cpu` (`IndexFlatIP`)
- **Testing & Benchmarking**: `pytest`
- **Output Formats**: Standard Library `json`, Standalone HTML5 + CSS3 + Vanilla JS

---

## 5. Phased Implementation Roadmap

| Phase | Responsibility / Component | Status |
| :---: | :--- | :---: |
| **1** | Project Foundation & Type-Safe Dataclasses | Complete |
| **2** | Native PDF Text & Metadata Ingestion | Complete |
| **3** | Text Normalization & Paragraph/Sentence Segmentation | Complete |
| **4** | Deterministic Exact Matching ($O(N+M)$ Hash Keying) | Complete |
| **5** | Semantic Vector Embedding & FAISS Candidate Retrieval | Complete |
| **6** | Multi-Signal Candidate Alignment & 1-to-1 Assignment | Complete |
| **7** | Content-Aware Structural Entity Change Detection | Complete |
| **8** | Final Classification, Severity & Confidence Scoring | Complete |
| **9** | End-to-End Pipeline Integration (`ComparisonEngine`) | Complete |
| **10** | Machine-Readable JSON Export & Standalone HTML Report | Complete |
| **11** | Edge-Case Hardening, XSS Escaping & Performance Benchmarks | Complete |
| **12** | Final Documentation, Packaging & Demo Dataset | Complete |

---

## 6. Key Algorithms & Complexity Breakdown

1. **Exact Matching ($O(N + M)$)**: Hashes normalized chunk text into an inverted lookup table. Matches identical content instantly, avoiding expensive vector operations for unchanged clauses.
2. **Semantic Vector Retrieval ($O(U \cdot K)$)**: Computes 384-dimensional embeddings for unresolved chunks ($U$) using `all-MiniLM-L6-v2`. Uses FAISS cosine similarity (`IndexFlatIP`) to retrieve Top-K candidate matches.
3. **Multi-Signal Alignment ($O(P \log P)$)**: Computes composite correspondence scores across candidates ($P$) using a weighted multi-signal formula:
   $$\text{Score} = 0.45 \cdot \text{Semantic} + 0.20 \cdot \text{Lexical} + 0.15 \cdot \text{Section} + 0.10 \cdot \text{Entity} + 0.05 \cdot \text{Type} + 0.05 \cdot \text{Position}$$
   Assigns target chunks using greedy 1-to-1 matching with deterministic tie-breaking.
4. **Structural Entity Analysis**: Evaluates aligned pairs using deterministic regular expressions and canonical normalizers for currencies (`$10,000`), percentages (`5%`), dates (`1 Jan 2026`), durations (`30 days`), and obligation modalities (`must` vs `may`).

---

## 7. Performance Benchmarks

Actual Phase 11 measurements on Windows CPU:

| Metric | Measured Value |
| :--- | :--- |
| **Cold-Start Latency** *(Includes initial model load)* | **~0.092 s** |
| **Warm Execution Latency** *(10 pages, 300 chunks)* | **~0.020 s (20 ms)** |
| **Total Test Suite Execution** | **100 Passed in 30.77s** |

### Per-Phase Processing Latency (10 Pages, 300 Chunks)
- **PDF Extraction**: `138.95 ms`
- **Document Segmentation**: `11.33 ms`
- **Exact Matching**: `0.40 ms`
- **FAISS Candidate Retrieval**: `0.01 ms`
- **Multi-Signal Alignment**: `0.01 ms`
- **Classification & Structural Analysis**: `0.18 ms`
- **HTML Report Generation**: `1.31 ms`
- **JSON Export Generation**: `9.79 ms`

---

## 8. Security & Robustness
- **XSS Safety**: 100% of PDF document text, section titles, and rationale explanations are escaped via `html.escape()` prior to rendering HTML report templates.
- **Error Handling**: Corrupt PDFs, missing files, or empty documents raise explicit `PDFExtractionError` exceptions without exposing Python stack traces in the CLI.

---

## 9. Quickstart & Installation

```bash
# 1. Clone repository
git clone https://github.com/Akshay122130/hybrid-semantic-pdf-comparator.git
cd hybrid-semantic-pdf-comparator

# 2. Set up virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

# 3. Install project in editable mode
pip install -e .

# 4. Run full test suite (100 tests)
python -m pytest
```

---

## 10. CLI Usage & Demonstration

### Version Control & Demo Artifact Handling
- **Version-Controlled Inputs**: `demo/source_contract.pdf` and `demo/target_contract.pdf` are committed demo inputs.
- **Generated Report Output**: `demo/reports/` contains generated HTML and JSON report outputs.
- **Git Exclusion**: `demo/reports/` is generated output and is intentionally excluded from Git via `.gitignore`. Do not commit generated reports to Git.

### Regenerate Demo Reports
Run the comparison CLI to populate or update `demo/reports/`:

```bash
python -m pdf_comparator.main demo/source_contract.pdf demo/target_contract.pdf --output-dir demo/reports
```

### CLI Terminal Summary Output
```text
PDF Comparison Complete

Source: source_contract.pdf
Target: target_contract.pdf

Unchanged: 6
Modified: 3
Added: 2
Removed: 0

High severity: 1
Medium severity: 0
Low severity: 4

Processing time: 4.08s

Reports:
HTML: demo\reports\comparison_report.html
JSON: demo\reports\comparison_report.json
```


---

## 11. Sample Use Case

### Source Clause
> *"The supplier must pay $10,000 within 30 days of invoice receipt."*

### Target Clause
> *"The supplier may pay $12,000 within 45 days of invoice receipt."*

### Engine Classification
- **Status**: `MODIFIED`
- **Severity**: `HIGH`
- **Confidence**: `89.7%`
- **Structural Changes**:
  - `MODALITY_CHANGE`: `must` $\rightarrow$ `may`
  - `CURRENCY_CHANGE`: `$10,000` $\rightarrow$ `$12,000`
  - `DURATION_CHANGE`: `30 days` $\rightarrow$ `45 days`

---

## 12. Known System Limitations
- **OCR Fallback**: `src/pdf_comparator/ingestion/ocr.py` remains a non-active placeholder. Scanned image-only PDFs requiring OCR are currently outside the active pipeline.
- **Specialized Table Grid Extraction**: `src/pdf_comparator/ingestion/table.py` remains a placeholder. Table text flows through standard sentence segmentation rather than custom 2D grid matrix alignment.
- **Rule-Based Severity Policies**: Severity rules are PoC heuristics and do not constitute legal advice.

---

## 13. Future Extensions
1. Integration of Tesseract OCR fallback for scanned PDFs.
2. 2D grid table cell structure comparison.
3. PDF visual bounding-box overlay highlighting.
4. Persistent embedding cache for large document repositories.
5. REST API wrapper (`FastAPI`).
