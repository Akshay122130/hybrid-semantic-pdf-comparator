"""Text cleaning and normalization module."""

import re
import unicodedata

# Regex to detect word-break hyphens across line breaks: e.g., "re-\nquire" -> "require"
HYPHENATED_LINEBREAK_RE = re.compile(r"(\b[A-Za-z]+)-\s*\n\s*([a-z]+)")

# Regex to match single line breaks that should be converted to space
SINGLE_LINEBREAK_RE = re.compile(r"(?<!\n)\n(?!\n)")

# Regex for repeated whitespace (spaces/tabs)
REPEATED_WHITESPACE_RE = re.compile(r"[ \t]+")

# Regex for control characters (excluding newline and tab during early passes)
CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def normalize_unicode(text: str) -> str:
    """Normalize Unicode characters and remove non-printable control characters."""
    if not text:
        return ""
    # Convert NFKC Unicode form and replace non-breaking spaces
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00a0", " ")
    # Remove control characters
    text = CONTROL_CHARS_RE.sub("", text)
    return text


def fix_line_breaks_and_hyphenation(text: str) -> str:
    """Fix PDF line-wrapping artifacts and safe hyphenation across line breaks."""
    if not text:
        return ""
    # Safe hyphenation across line breaks: "develop-\n-ment" -> "development"
    text = HYPHENATED_LINEBREAK_RE.sub(r"\1\2", text)
    # Replace single line breaks with spaces to merge wrapped lines
    text = SINGLE_LINEBREAK_RE.sub(" ", text)
    return text


def collapse_whitespace(text: str) -> str:
    """Collapse repeated spaces and tabs into a single space and strip edges."""
    if not text:
        return ""
    text = REPEATED_WHITESPACE_RE.sub(" ", text)
    return text.strip()


def clean_text(text: str) -> str:
    """Clean raw extracted text into normalized text.

    Preserves original numbers, dates, currencies, punctuation, and symbols while
    fixing PDF line wrapping, hyphenation across lines, and whitespace noise.
    """
    if not text:
        return ""
    text = normalize_unicode(text)
    text = fix_line_breaks_and_hyphenation(text)
    text = collapse_whitespace(text)
    return text
