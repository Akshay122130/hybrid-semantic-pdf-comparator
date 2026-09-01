"""Script to generate realistic synthetic demonstration PDFs for Hybrid Semantic PDF Comparator."""

import os
import fitz
from pathlib import Path


def build_demo_pdfs():
    demo_dir = Path(__file__).parent
    demo_dir.mkdir(parents=True, exist_ok=True)

    source_path = demo_dir / "source_contract.pdf"
    target_path = demo_dir / "target_contract.pdf"

    # Source Contract Document
    doc_a = fitz.open()

    # Page 1
    p1_a = doc_a.new_page()
    lines_p1_a = [
        "MASTER SERVICES AND SOFTWARE LICENSE AGREEMENT",
        "Section 1. Scope of Agreement",
        "This Master Services Agreement ('Agreement') is entered into between Provider Inc. and Client Corp.",
        "Section 2. Payment & Financial Terms",
        "The supplier must pay $10,000 within 30 days of invoice receipt.",
        "All payments shall be made in USD via wire transfer.",
        "Section 3. Warranty & Liability",
        "Provider warrants that the software performance complies with agreed specifications.",
        "Provider shall retain exclusive title to all pre-existing IP.",
    ]
    y = 50
    for line in lines_p1_a:
        p1_a.insert_text((50, y), line, fontsize=11 if not line.isupper() else 14)
        y += 28

    doc_a.save(str(source_path))
    doc_a.close()

    # Target Contract Document (with intentional modifications, additions, and removals)
    doc_b = fitz.open()

    # Page 1
    p1_b = doc_b.new_page()
    lines_p1_b = [
        "MASTER SERVICES AND SOFTWARE LICENSE AGREEMENT",
        "Section 1. Scope of Agreement",
        "This Master Services Agreement ('Agreement') is entered into between Provider Inc. and Client Corp.",
        "Section 2. Payment & Financial Terms",
        "The supplier may pay $12,000 within 45 days of invoice receipt.",  # MODIFIED: must->may, $10k->$12k, 30d->45d
        "All payments shall be made in USD via wire transfer.",  # UNCHANGED
        "Section 3. Confidentiality",  # ADDED SECTION
        "Each party agrees to hold all proprietary confidential information in strict confidence.",  # ADDED CLAUSE
        "Section 4. Warranty & Intellectual Property",
        "Provider warrants that application performance complies with agreed specifications.",  # MODIFIED: software->application
        "Provider shall retain exclusive title to all pre-existing IP.",  # UNCHANGED
    ]
    y = 50
    for line in lines_p1_b:
        p1_b.insert_text((50, y), line, fontsize=11 if not line.isupper() else 14)
        y += 28

    doc_b.save(str(target_path))
    doc_b.close()

    print(f"Generated demo source PDF: {source_path}")
    print(f"Generated demo target PDF: {target_path}")


if __name__ == "__main__":
    build_demo_pdfs()
