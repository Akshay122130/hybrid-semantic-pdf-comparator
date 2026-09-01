"""Document segmentation module converting raw extracted blocks into hierarchical Chunk objects."""

import re
from typing import List, Optional

from pdf_comparator.core.models import Chunk, ChunkType
from pdf_comparator.ingestion.extractor import RawDocument
from pdf_comparator.processing.cleaner import clean_text

COMMON_ABBREVIATIONS = {
    "e.g.", "i.e.", "dr.", "mr.", "mrs.", "ms.", "prof.", "sr.", "jr.",
    "vs.", "v.", "no.", "inc.", "co.", "ltd.", "jan.", "feb.", "mar.",
    "apr.", "aug.", "sept.", "oct.", "nov.", "dec.", "sect.", "art.",
    "para.", "fig.", "eq.", "approx.", "etc.", "vol.", "pp."
}

HEADING_PATTERNS = [
    re.compile(r"^(section|chapter|article|appendix)\s+([0-9a-z\.]+)", re.IGNORECASE),
    re.compile(r"^[0-9]+(\.[0-9]+)*\s+[A-Z]"),
]

LIST_ITEM_PATTERNS = [
    re.compile(r"^[\u2022\u2023\u25e6\u2043\u2219\u2013\u2014\*\-]\s+"),  # Bullet symbols
    re.compile(r"^(\d+|[a-zA-Z]|[ivxLCDM]+)[\.\)]\s+"),                  # 1., a), i.
    re.compile(r"^\((\d+|[a-zA-Z]|[ivxLCDM]+)\)\s+"),                    # (1), (a), (i)
]


def is_list_item(text: str) -> bool:
    """Detect if raw text block starts with a list item indicator."""
    cleaned = text.strip()
    for pat in LIST_ITEM_PATTERNS:
        if pat.match(cleaned):
            return True
    return False


def is_heading(text: str) -> bool:
    """Detect if raw text block represents a section heading using layout and text heuristics."""
    cleaned = text.strip()
    if not cleaned:
        return False

    for pat in HEADING_PATTERNS:
        if pat.match(cleaned):
            return True

    lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
    if len(lines) == 1:
        line = lines[0]
        # Short standalone line without ending punctuation, starting with uppercase
        if len(line) <= 60 and not line.endswith(".") and line[0].isupper():
            if not is_list_item(line):
                return True

    return False


def split_sentences(text: str) -> List[str]:
    """Split paragraph text into sentences while protecting common abbreviations."""
    if not text:
        return []

    # Split on period, exclamation, or question mark followed by whitespace and capital letter/digit
    raw_splits = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\'\(\$])', text.strip())

    sentences: List[str] = []
    buffer = ""

    for segment in raw_splits:
        if buffer:
            buffer += " " + segment
        else:
            buffer = segment

        # Check if the buffer ends with a protected abbreviation
        tokens = buffer.rstrip().split()
        last_word = tokens[-1].lower() if tokens else ""
        if last_word in COMMON_ABBREVIATIONS:
            continue
        else:
            sentences.append(buffer)
            buffer = ""

    if buffer:
        sentences.append(buffer)

    return [s for s in sentences if s.strip()]


class DocumentSegmenter:
    """Segments RawDocument pages and blocks into sentence-level Chunk objects."""

    def segment(self, raw_doc: RawDocument, doc_prefix: str = "doc") -> List[Chunk]:
        """Convert a RawDocument into an ordered list of Chunk objects.

        Args:
            raw_doc: Extracted RawDocument structure.
            doc_prefix: Namespace prefix for generating unique chunk IDs.

        Returns:
            List of structured Chunk instances.
        """
        chunks: List[Chunk] = []
        current_section: Optional[str] = None

        for page in raw_doc.pages:
            for block in page.blocks:
                # Skip non-text blocks
                if block.block_type != 0:
                    continue

                raw_text = block.text
                cleaned_block_text = clean_text(raw_text)

                if not cleaned_block_text:
                    continue

                paragraph_id = f"{doc_prefix}_p{page.page_num}_b{block.block_index}"

                # Determine chunk type
                if is_heading(raw_text):
                    chunk_type = ChunkType.HEADING
                    current_section = cleaned_block_text
                elif is_list_item(raw_text):
                    chunk_type = ChunkType.LIST_ITEM
                else:
                    chunk_type = ChunkType.TEXT

                # Break block into sentence segments if standard text
                if chunk_type == ChunkType.TEXT:
                    raw_sentences = split_sentences(raw_text)
                else:
                    raw_sentences = [raw_text]

                if not raw_sentences:
                    raw_sentences = [raw_text]

                total_sentences = len(raw_sentences)

                for sentence_idx, sentence_raw in enumerate(raw_sentences):
                    sentence_clean = clean_text(sentence_raw)
                    if not sentence_clean:
                        continue

                    # Calculate approximate bounding box per sentence
                    if total_sentences == 1 or block.bbox is None:
                        sentence_bbox = block.bbox
                    else:
                        x0, y0, x1, y1 = block.bbox
                        height = y1 - y0
                        y0_i = round(y0 + (sentence_idx / total_sentences) * height, 2)
                        y1_i = round(y0 + ((sentence_idx + 1) / total_sentences) * height, 2)
                        sentence_bbox = (x0, y0_i, x1, y1_i)

                    chunk_id = f"{paragraph_id}_s{sentence_idx}"

                    chunk = Chunk(
                        id=chunk_id,
                        paragraph_id=paragraph_id,
                        original_text=sentence_raw,
                        normalized_text=sentence_clean,
                        page_num=page.page_num,
                        section=current_section,
                        bbox=sentence_bbox,
                        type=chunk_type,
                        metadata={
                            "block_index": block.block_index,
                            "sentence_index": sentence_idx,
                        },
                    )
                    chunks.append(chunk)

        return chunks
