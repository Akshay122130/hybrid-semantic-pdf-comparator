"""Unit tests for text cleaner and normalization functions."""

from pdf_comparator.processing.cleaner import clean_text, collapse_whitespace, normalize_unicode


def test_whitespace_normalization():
    """Test repeated whitespace and tab collapsing."""
    raw = "This   is   a   test  \t  with   extra   spaces."
    cleaned = clean_text(raw)
    assert cleaned == "This is a test with extra spaces."


def test_line_break_normalization():
    """Test line-break removal within a single paragraph block."""
    raw = "First line of text\nsecond line of text\nthird line of text."
    cleaned = clean_text(raw)
    assert cleaned == "First line of text second line of text third line of text."


def test_safe_hyphenation_handling():
    """Test safe de-hyphenation across line breaks."""
    raw = "The system require-\nments state that re-\nquire is de-hyphenated."
    cleaned = clean_text(raw)
    assert cleaned == "The system requirements state that require is de-hyphenated."


def test_preservation_of_numbers_dates_and_punctuation():
    """Test that numbers, currencies, dates, and symbols are untouched during normalization."""
    raw = "Agreement dated 2026-09-01: Amount is $5,000.00 (50% deposit required; €4,200)."
    cleaned = clean_text(raw)
    assert cleaned == "Agreement dated 2026-09-01: Amount is $5,000.00 (50% deposit required; €4,200)."


def test_unicode_and_control_char_cleaning():
    """Test non-breaking space replacement and control character stripping."""
    raw = "Hello\u00a0World\x00\x07!"
    cleaned = clean_text(raw)
    assert cleaned == "Hello World!"


def test_empty_and_none_text():
    """Test empty string handling."""
    assert clean_text("") == ""
    assert clean_text("   \n\t  ") == ""
