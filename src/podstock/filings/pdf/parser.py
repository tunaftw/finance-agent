"""PDF parsing utilities using pymupdf4llm.

This module provides high-performance PDF to Markdown conversion,
optimized for LLM consumption.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class PDFParser:
    """PDF parser using pymupdf4llm for fast Markdown conversion.

    pymupdf4llm provides the best balance of speed and quality for
    converting PDFs to LLM-friendly Markdown format.

    Example:
        >>> parser = PDFParser()
        >>> markdown = parser.to_markdown("/path/to/report.pdf")
        >>> print(markdown[:500])
    """

    def __init__(self, *, extract_images: bool = False):
        """Initialize the PDF parser.

        Args:
            extract_images: Whether to extract and include images.
                           Disabled by default for speed.
        """
        self.extract_images = extract_images
        self._pymupdf4llm = None

    def _ensure_pymupdf4llm(self) -> None:
        """Lazy import pymupdf4llm."""
        if self._pymupdf4llm is None:
            try:
                import pymupdf4llm

                self._pymupdf4llm = pymupdf4llm
            except ImportError as e:
                raise ImportError(
                    "pymupdf4llm is required for PDF parsing. "
                    "Install with: pip install pymupdf4llm"
                ) from e

    def to_markdown(self, pdf_path: str | Path) -> str:
        """Convert a PDF to Markdown.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Markdown representation of the PDF content.

        Raises:
            FileNotFoundError: If the PDF file doesn't exist.
            PDFParseError: If parsing fails.
        """
        from podstock.filings.exceptions import PDFParseError

        self._ensure_pymupdf4llm()

        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        try:
            return self._pymupdf4llm.to_markdown(
                str(path),
                show_progress=False,
                write_images=self.extract_images,
            )
        except Exception as e:
            raise PDFParseError(str(path), str(e)) from e

    def to_markdown_pages(self, pdf_path: str | Path) -> list[str]:
        """Convert a PDF to Markdown, returning content per page.

        Useful for page-based chunking strategies.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of Markdown strings, one per page.

        Raises:
            FileNotFoundError: If the PDF file doesn't exist.
            PDFParseError: If parsing fails.
        """
        from podstock.filings.exceptions import PDFParseError

        self._ensure_pymupdf4llm()

        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        try:
            # pymupdf4llm returns a list when pages are requested separately
            result = self._pymupdf4llm.to_markdown(
                str(path),
                show_progress=False,
                write_images=self.extract_images,
                page_chunks=True,  # Return per-page content
            )
            # Result is list of dicts with 'text' key
            if isinstance(result, list):
                return [page.get("text", "") for page in result]
            return [result]
        except Exception as e:
            raise PDFParseError(str(path), str(e)) from e

    def get_page_count(self, pdf_path: str | Path) -> int:
        """Get the number of pages in a PDF.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Number of pages.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise ImportError(
                "PyMuPDF is required for PDF operations. "
                "Install with: pip install pymupdf"
            ) from e

        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        with fitz.open(str(path)) as doc:
            return len(doc)

    def get_metadata(self, pdf_path: str | Path) -> dict:
        """Extract metadata from a PDF.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Dictionary with PDF metadata (title, author, creation date, etc.).
        """
        try:
            import fitz
        except ImportError as e:
            raise ImportError(
                "PyMuPDF is required for PDF operations. "
                "Install with: pip install pymupdf"
            ) from e

        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        with fitz.open(str(path)) as doc:
            return dict(doc.metadata)
