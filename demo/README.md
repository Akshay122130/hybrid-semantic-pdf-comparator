# Demonstration & Sample Contracts

This directory contains demonstration PDF input documents and scripts for evaluating the **Hybrid Semantic PDF Comparison Engine**.

## Demo Files & Version Control
- **Version-Controlled Inputs**:
  - `source_contract.pdf`: Baseline version of a Master Services Agreement (committed to Git).
  - `target_contract.pdf`: Revised version containing intentional modifications, additions, and structural shifts (committed to Git).
  - `generate_demo_pdfs.py`: Script that programmatically builds `source_contract.pdf` and `target_contract.pdf` using PyMuPDF.

- **Generated Output Artifacts (Excluded from Git)**:
  - `demo/reports/`: Directory containing generated HTML and JSON comparison reports.
  - **Git Exclusion**: `demo/reports/` contains generated build artifacts and is intentionally excluded from version control (`.gitignore`). Do not add generated report files to Git.

## Regenerating Demo Reports
Users can regenerate the comparison reports at any time by running:

```bash
python -m pdf_comparator.main demo/source_contract.pdf demo/target_contract.pdf --output-dir demo/reports
```

This command populates:
- `demo/reports/comparison_report.html`: Standalone, interactive visual HTML report with filter tabs, search, and structural diff tables.
- `demo/reports/comparison_report.json`: Machine-readable JSON comparison summary for downstream automation.

## Expected Comparison Scenarios
Running the comparison on these synthetic contracts demonstrates:
1. **`UNCHANGED`**: Standard boilerplate clauses (Section 1 scope, wire transfer payment method, IP title retention).
2. **`MODIFIED` (HIGH Severity)**: Section 2 payment terms shift (`must` $\rightarrow$ `may`, `$10,000` $\rightarrow$ `$12,000`, `30 days` $\rightarrow$ `45 days`).
3. **`MODIFIED` (LOW Severity)**: Section 4 warranty wording tweak (`software` $\rightarrow$ `application`).
4. **`ADDED`**: Section 3 newly inserted confidentiality clause.
