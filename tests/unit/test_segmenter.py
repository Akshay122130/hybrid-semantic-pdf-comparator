"""Unit tests for DocumentSegmenter and segmentation helpers."""

from pdf_comparator.core.models import ChunkType
from pdf_comparator.ingestion.extractor import RawBlock, RawDocument, RawPage
from pdf_comparator.processing.segmenter import (
    DocumentSegmenter,
    is_heading,
    is_list_item,
    split_sentences,
)


def test_is_heading():
    """Test section heading classification heuristics."""
    assert is_heading("Section 1. Introduction") is True
    assert is_heading("1.0 Scope of Work") is True
    assert is_heading("TERMS AND CONDITIONS") is True
    assert is_heading("This is a normal paragraph sentence ending with a period.") is False


def test_is_list_item():
    """Test list item detection for bullets and numbers."""
    assert is_list_item("• First item in list") is True
    assert is_list_item("- Second item in list") is True
    assert is_list_item("1. Numbered item") is True
    assert is_list_item("(a) Sub-clause item") is True
    assert is_list_item("Normal sentence without list indicator.") is False


def test_split_sentences_with_abbreviations():
    """Test sentence splitting while preserving abbreviations such as e.g., i.e., Dr., vs."""
    text = "The agreement e.g. section 3 applies. Payment is due in 30 days. Contact Dr. Smith."
    sentences = split_sentences(text)

    assert len(sentences) == 3
    assert sentences[0] == "The agreement e.g. section 3 applies."
    assert sentences[1] == "Payment is due in 30 days."
    assert sentences[2] == "Contact Dr. Smith."


def test_segmenter_full_pipeline_multi_page():
    """Test DocumentSegmenter with multi-page RawDocument containing headings, paragraphs, and list items."""
    page1 = RawPage(
        page_num=1,
        width=595.0,
        height=842.0,
        blocks=[
            RawBlock(
                block_index=0,
                text="Section 1. Obligations\n",
                bbox=(50.0, 50.0, 500.0, 70.0),
                block_type=0,
            ),
            RawBlock(
                block_index=1,
                text="The Contractor shall deliver the software. Payment is due in 30 days.\n",
                bbox=(50.0, 80.0, 500.0, 120.0),
                block_type=0,
            ),
            RawBlock(
                block_index=2,
                text="• Deliverable A: Source Code\n",
                bbox=(50.0, 130.0, 500.0, 150.0),
                block_type=0,
            ),
            RawBlock(
                block_index=3,
                text="   \n",  # Empty block to ignore
                bbox=(50.0, 160.0, 500.0, 170.0),
                block_type=0,
            ),
        ],
        has_text=True,
    )

    page2 = RawPage(
        page_num=2,
        width=595.0,
        height=842.0,
        blocks=[
            RawBlock(
                block_index=0,
                text="Late fees apply for delayed payments.\n",
                bbox=(50.0, 50.0, 500.0, 80.0),
                block_type=0,
            ),
        ],
        has_text=True,
    )

    raw_doc = RawDocument(
        file_path="test.pdf",
        total_pages=2,
        pages=[page1, page2],
    )

    segmenter = DocumentSegmenter()
    chunks = segmenter.segment(raw_doc, doc_prefix="test_doc")

    # Should produce:
    # Page 1, Block 0: Heading -> 1 chunk
    # Page 1, Block 1: 2 sentences -> 2 chunks
    # Page 1, Block 2: List item -> 1 chunk
    # Page 1, Block 3: Empty -> 0 chunks
    # Page 2, Block 0: 1 sentence -> 1 chunk (inherits section from Page 1 heading)
    assert len(chunks) == 5

    # Check Chunk 0 (Heading)
    c0 = chunks[0]
    assert c0.id == "test_doc_p1_b0_s0"
    assert c0.paragraph_id == "test_doc_p1_b0"
    assert c0.type == ChunkType.HEADING
    assert c0.section == "Section 1. Obligations"
    assert c0.page_num == 1
    assert c0.original_text == "Section 1. Obligations\n"
    assert c0.normalized_text == "Section 1. Obligations"

    # Check Chunk 1 (Sentence 1 of Block 1)
    c1 = chunks[1]
    assert c1.id == "test_doc_p1_b1_s0"
    assert c1.paragraph_id == "test_doc_p1_b1"
    assert c1.type == ChunkType.TEXT
    assert c1.section == "Section 1. Obligations"
    assert c1.normalized_text == "The Contractor shall deliver the software."

    # Check Chunk 2 (Sentence 2 of Block 1)
    c2 = chunks[2]
    assert c2.id == "test_doc_p1_b1_s1"
    assert c2.paragraph_id == "test_doc_p1_b1"
    assert c2.type == ChunkType.TEXT
    assert c2.section == "Section 1. Obligations"
    assert c2.normalized_text == "Payment is due in 30 days."

    # Check Chunk 3 (List Item)
    c3 = chunks[3]
    assert c3.id == "test_doc_p1_b2_s0"
    assert c3.type == ChunkType.LIST_ITEM

    # Check Chunk 4 (Page 2)
    c4 = chunks[4]
    assert c4.id == "test_doc_p2_b0_s0"
    assert c4.page_num == 2
    assert c4.section == "Section 1. Obligations"
    assert c4.normalized_text == "Late fees apply for delayed payments."


def test_unique_chunk_ids_and_metadata():
    """Verify chunk ID uniqueness and bbox preservation."""
    page = RawPage(
        page_num=1,
        width=595.0,
        height=842.0,
        blocks=[
            RawBlock(
                block_index=0,
                text="Sentence A. Sentence B.",
                bbox=(10.0, 20.0, 100.0, 60.0),
                block_type=0,
            )
        ],
        has_text=True,
    )
    raw_doc = RawDocument(file_path="sample.pdf", total_pages=1, pages=[page])

    segmenter = DocumentSegmenter()
    chunks = segmenter.segment(raw_doc, doc_prefix="sample")

    assert len(chunks) == 2
    ids = [c.id for c in chunks]
    assert len(ids) == len(set(ids))  # Guarantee unique IDs

    # Check bbox subdivision
    assert chunks[0].bbox == (10.0, 20.0, 100.0, 40.0)
    assert chunks[1].bbox == (10.0, 40.0, 100.0, 60.0)
