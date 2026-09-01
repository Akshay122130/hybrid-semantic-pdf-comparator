"""Text cleaning and document segmentation module."""

from pdf_comparator.processing.cleaner import clean_text, collapse_whitespace, normalize_unicode
from pdf_comparator.processing.segmenter import DocumentSegmenter, is_heading, is_list_item, split_sentences

__all__ = [
    "clean_text",
    "collapse_whitespace",
    "normalize_unicode",
    "DocumentSegmenter",
    "is_heading",
    "is_list_item",
    "split_sentences",
]
