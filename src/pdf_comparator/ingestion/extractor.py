"""Native PDF text and metadata extraction using PyMuPDF."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Union

import fitz


class PDFExtractionError(Exception):
    """Exception raised when PDF extraction fails due to invalid files or read errors."""
    pass


@dataclass
class RawBlock:
    """Raw content block extracted from a single PDF page.
    
    Preserves original, unmodified text along with spatial bounding box and block order.
    """
    block_index: int
    text: str
    bbox: Tuple[float, float, float, float]
    block_type: int = 0  # 0: Text, 1: Image/Graphic


@dataclass
class RawPage:
    """Raw layout and content structure for a single PDF page."""
    page_num: int  # 1-based page index
    width: float
    height: float
    blocks: List[RawBlock] = field(default_factory=list)
    has_text: bool = False


@dataclass
class RawDocument:
    """Extracted raw content representation of a PDF document."""
    file_path: str
    total_pages: int
    pages: List[RawPage] = field(default_factory=list)


class PDFExtractor:
    """Extracts native text, page metadata, and block bounding boxes from PDF files."""

    def extract(self, file_path: Union[str, Path]) -> RawDocument:
        """Extract page-by-page raw text blocks and metadata from a PDF file.

        Args:
            file_path: Path to the PDF file.

        Returns:
            RawDocument containing page-wise extracted blocks and metadata.

        Raises:
            FileNotFoundError: If the PDF file path does not exist.
            PDFExtractionError: If the PDF is corrupt or unreadable.
        """
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        try:
            doc = fitz.open(path)
        except Exception as e:
            raise PDFExtractionError(f"Failed to open or read PDF file '{file_path}': {e}") from e

        try:
            raw_pages: List[RawPage] = []
            for page_index in range(len(doc)):
                page_num = page_index + 1
                try:
                    page = doc[page_index]
                    rect = page.rect
                    width, height = rect.width, rect.height

                    blocks: List[RawBlock] = []
                    raw_blocks = page.get_text("blocks")
                    for b in raw_blocks:
                        if len(b) >= 7:
                            x0, y0, x1, y1, text, block_no, block_type = b[:7]
                            raw_block = RawBlock(
                                block_index=int(block_no),
                                text=str(text),
                                bbox=(float(x0), float(y0), float(x1), float(y1)),
                                block_type=int(block_type),
                            )
                            blocks.append(raw_block)

                    has_text = any(b.text.strip() for b in blocks if b.block_type == 0)
                    raw_pages.append(
                        RawPage(
                            page_num=page_num,
                            width=width,
                            height=height,
                            blocks=blocks,
                            has_text=has_text,
                        )
                    )
                except Exception as page_err:
                    raise PDFExtractionError(
                        f"Error processing page {page_num} of '{file_path}': {page_err}"
                    ) from page_err

            return RawDocument(
                file_path=str(path),
                total_pages=len(doc),
                pages=raw_pages,
            )
        finally:
            doc.close()
