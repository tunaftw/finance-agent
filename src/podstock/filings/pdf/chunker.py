"""Document chunking strategies for financial filings.

This module implements multi-pass hierarchical chunking to handle
large financial reports without filling up LLM context windows.

Strategy:
1. Extract document structure (TOC, sections)
2. Extract tables separately with pdfplumber
3. Chunk text with overlap, prepending document-level metadata
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from podstock.filings.models import DocumentChunk, Filing


class ChunkingStrategy(str, Enum):
    """Available chunking strategies."""

    PAGE_BASED = "page"  # Simple: one chunk per page
    FIXED_SIZE = "fixed"  # Fixed token count per chunk
    SECTION_BASED = "section"  # Identify sections first
    HYBRID = "hybrid"  # Combined approach


@dataclass
class ChunkConfig:
    """Configuration for chunking behavior.

    Attributes:
        max_tokens: Maximum tokens per chunk (default: 6000).
        overlap_tokens: Token overlap between chunks (default: 200).
        strategy: Chunking strategy to use.
        include_metadata: Whether to prepend document metadata.
        pages_per_chunk: For page-based strategy, pages per chunk.
    """

    max_tokens: int = 6000
    overlap_tokens: int = 200
    strategy: ChunkingStrategy = ChunkingStrategy.HYBRID
    include_metadata: bool = True
    pages_per_chunk: int = 3


class FilingChunker:
    """Intelligent chunking for financial filings.

    Implements multi-pass chunking to handle large documents while
    preserving context for LLM analysis.

    The chunking process:
    1. Parse PDF to markdown (page by page)
    2. Identify section boundaries if possible
    3. Create chunks respecting section boundaries
    4. Prepend document-level metadata to each chunk

    Example:
        >>> from podstock.filings.pdf.chunker import FilingChunker
        >>> chunker = FilingChunker()
        >>> chunks = chunker.chunk_filing(filing, pdf_path)
        >>> for chunk in chunks:
        ...     print(f"Pages {chunk.page_start}-{chunk.page_end}")
    """

    # Common section patterns in financial filings
    SECTION_PATTERNS = [
        # 10-K / Annual Report sections
        r"(?i)^#+\s*(item\s+1[a-z]?\.?\s*)?business",
        r"(?i)^#+\s*(item\s+1a\.?\s*)?risk\s+factors",
        r"(?i)^#+\s*(item\s+7\.?\s*)?management.s\s+discussion",
        r"(?i)^#+\s*(item\s+8\.?\s*)?financial\s+statements",
        r"(?i)^#+\s*notes\s+to\s+(consolidated\s+)?financial\s+statements",
        # Swedish annual report sections
        r"(?i)^#+\s*f.rvaltningsber.ttelse",
        r"(?i)^#+\s*resultatr.kning",
        r"(?i)^#+\s*balansr.kning",
        r"(?i)^#+\s*kassafl.desanalys",
        r"(?i)^#+\s*noter",
        r"(?i)^#+\s*revisionsber.ttelse",
    ]

    def __init__(self, config: ChunkConfig | None = None):
        """Initialize the chunker.

        Args:
            config: Chunking configuration. Uses defaults if not provided.
        """
        self.config = config or ChunkConfig()
        self._parser = None

    def _get_parser(self):
        """Get or create PDF parser instance."""
        if self._parser is None:
            from podstock.filings.pdf.parser import PDFParser

            self._parser = PDFParser()
        return self._parser

    def chunk_filing(
        self,
        filing: Filing,
        pdf_path: str | Path,
    ) -> list[DocumentChunk]:
        """Chunk a filing for LLM processing.

        Args:
            filing: The Filing object with metadata.
            pdf_path: Path to the PDF file.

        Returns:
            List of DocumentChunk objects ready for analysis.

        Raises:
            ChunkingError: If chunking fails.
        """
        from podstock.filings.exceptions import ChunkingError
        from podstock.filings.models import DocumentChunk

        path = Path(pdf_path)
        if not path.exists():
            raise ChunkingError(filing.id, f"PDF not found: {path}")

        try:
            parser = self._get_parser()
            page_count = parser.get_page_count(path)

            if self.config.strategy == ChunkingStrategy.PAGE_BASED:
                return self._chunk_by_pages(filing, path, page_count)
            elif self.config.strategy == ChunkingStrategy.FIXED_SIZE:
                return self._chunk_by_tokens(filing, path)
            else:
                # HYBRID and SECTION_BASED use same logic
                return self._chunk_hybrid(filing, path, page_count)

        except Exception as e:
            if isinstance(e, ChunkingError):
                raise
            raise ChunkingError(filing.id, str(e)) from e

    def _chunk_by_pages(
        self,
        filing: Filing,
        pdf_path: Path,
        page_count: int,
    ) -> list[DocumentChunk]:
        """Simple page-based chunking."""
        from podstock.filings.models import DocumentChunk

        parser = self._get_parser()
        pages = parser.to_markdown_pages(pdf_path)

        chunks = []
        pages_per_chunk = self.config.pages_per_chunk

        for i in range(0, len(pages), pages_per_chunk):
            batch = pages[i : i + pages_per_chunk]
            content = "\n\n---\n\n".join(batch)

            page_start = i + 1
            page_end = min(i + pages_per_chunk, len(pages))

            # Add metadata header if configured
            if self.config.include_metadata:
                content = self._create_metadata_header(filing, page_start, page_end, page_count) + content

            chunk = DocumentChunk(
                chunk_id=self._generate_chunk_id(filing.id, i // pages_per_chunk),
                filing_id=filing.id,
                chunk_index=i // pages_per_chunk,
                page_start=page_start,
                page_end=page_end,
                content=content,
                word_count=len(content.split()),
            )
            chunks.append(chunk)

        return chunks

    def _chunk_by_tokens(
        self,
        filing: Filing,
        pdf_path: Path,
    ) -> list[DocumentChunk]:
        """Token-based chunking with overlap."""
        from podstock.filings.models import DocumentChunk

        parser = self._get_parser()
        full_text = parser.to_markdown(pdf_path)
        page_count = parser.get_page_count(pdf_path)

        # Rough token estimation (1 token ≈ 4 characters)
        chars_per_token = 4
        max_chars = self.config.max_tokens * chars_per_token
        overlap_chars = self.config.overlap_tokens * chars_per_token

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(full_text):
            end = min(start + max_chars, len(full_text))

            # Try to break at a paragraph boundary
            if end < len(full_text):
                # Look for paragraph break near the end
                break_point = full_text.rfind("\n\n", start + max_chars // 2, end)
                if break_point > start:
                    end = break_point

            content = full_text[start:end].strip()

            # Add metadata header
            if self.config.include_metadata:
                # Estimate page numbers (rough)
                estimated_page = int((start / len(full_text)) * page_count) + 1
                estimated_end_page = int((end / len(full_text)) * page_count) + 1
                content = (
                    self._create_metadata_header(filing, estimated_page, estimated_end_page, page_count) + content
                )

            chunk = DocumentChunk(
                chunk_id=self._generate_chunk_id(filing.id, chunk_index),
                filing_id=filing.id,
                chunk_index=chunk_index,
                page_start=1,  # Approximate
                page_end=page_count,  # Approximate
                content=content,
                word_count=len(content.split()),
            )
            chunks.append(chunk)

            # Move start with overlap
            start = end - overlap_chars
            chunk_index += 1

        return chunks

    def _chunk_hybrid(
        self,
        filing: Filing,
        pdf_path: Path,
        page_count: int,
    ) -> list[DocumentChunk]:
        """Hybrid chunking: identify sections, then chunk within them.

        For large documents, this provides better context preservation
        than pure page-based or token-based chunking.
        """
        import re

        from podstock.filings.models import DocumentChunk

        parser = self._get_parser()
        pages = parser.to_markdown_pages(pdf_path)

        # First pass: identify section boundaries
        sections = self._identify_sections(pages)

        # If no clear sections found, fall back to page-based
        if len(sections) <= 1:
            return self._chunk_by_pages(filing, pdf_path, page_count)

        # Second pass: create chunks respecting section boundaries
        chunks = []
        chunk_index = 0

        for section in sections:
            section_pages = pages[section["start_page"] : section["end_page"]]
            section_content = "\n\n---\n\n".join(section_pages)

            # If section is too large, split it further
            chars_per_token = 4
            max_chars = self.config.max_tokens * chars_per_token

            if len(section_content) > max_chars:
                # Split large sections
                sub_chunks = self._split_large_section(
                    section_content,
                    section["start_page"] + 1,
                    section["end_page"],
                    max_chars,
                )
                for sub_content, sub_start, sub_end in sub_chunks:
                    if self.config.include_metadata:
                        sub_content = self._create_metadata_header(
                            filing,
                            sub_start,
                            sub_end,
                            page_count,
                            section.get("type"),
                        ) + sub_content

                    chunk = DocumentChunk(
                        chunk_id=self._generate_chunk_id(filing.id, chunk_index),
                        filing_id=filing.id,
                        chunk_index=chunk_index,
                        page_start=sub_start,
                        page_end=sub_end,
                        section_type=section.get("type"),
                        content=sub_content,
                        word_count=len(sub_content.split()),
                    )
                    chunks.append(chunk)
                    chunk_index += 1
            else:
                # Section fits in one chunk
                if self.config.include_metadata:
                    section_content = self._create_metadata_header(
                        filing,
                        section["start_page"] + 1,
                        section["end_page"],
                        page_count,
                        section.get("type"),
                    ) + section_content

                chunk = DocumentChunk(
                    chunk_id=self._generate_chunk_id(filing.id, chunk_index),
                    filing_id=filing.id,
                    chunk_index=chunk_index,
                    page_start=section["start_page"] + 1,
                    page_end=section["end_page"],
                    section_type=section.get("type"),
                    content=section_content,
                    word_count=len(section_content.split()),
                )
                chunks.append(chunk)
                chunk_index += 1

        return chunks

    def _identify_sections(self, pages: list[str]) -> list[dict]:
        """Identify section boundaries in the document.

        Returns list of dicts with:
        - start_page: 0-based page index
        - end_page: 0-based page index (exclusive)
        - type: Section type if identified (e.g., "financial_statements")
        """
        import re

        sections = []
        current_section = {"start_page": 0, "end_page": 0, "type": None}

        for page_idx, page_content in enumerate(pages):
            for pattern in self.SECTION_PATTERNS:
                if re.search(pattern, page_content, re.MULTILINE):
                    # Found a section boundary
                    if page_idx > current_section["start_page"]:
                        current_section["end_page"] = page_idx
                        sections.append(current_section)

                    # Determine section type from pattern
                    section_type = self._infer_section_type(pattern)
                    current_section = {
                        "start_page": page_idx,
                        "end_page": page_idx,
                        "type": section_type,
                    }
                    break

        # Add final section
        current_section["end_page"] = len(pages)
        sections.append(current_section)

        return sections

    def _infer_section_type(self, pattern: str) -> str | None:
        """Infer section type from matched pattern."""
        pattern_lower = pattern.lower()
        if "financial" in pattern_lower or "statements" in pattern_lower:
            return "financial_statements"
        elif "management" in pattern_lower or "discussion" in pattern_lower:
            return "mda"
        elif "risk" in pattern_lower:
            return "risk_factors"
        elif "notes" in pattern_lower:
            return "notes"
        elif "business" in pattern_lower:
            return "business"
        elif "resultat" in pattern_lower:
            return "income_statement"
        elif "balans" in pattern_lower:
            return "balance_sheet"
        elif "kassafl" in pattern_lower:
            return "cash_flow"
        return None

    def _split_large_section(
        self,
        content: str,
        start_page: int,
        end_page: int,
        max_chars: int,
    ) -> list[tuple[str, int, int]]:
        """Split a large section into smaller chunks."""
        chunks = []
        overlap = self.config.overlap_tokens * 4  # chars

        start = 0
        total_pages = end_page - start_page + 1

        while start < len(content):
            end = min(start + max_chars, len(content))

            # Try to break at paragraph
            if end < len(content):
                break_point = content.rfind("\n\n", start + max_chars // 2, end)
                if break_point > start:
                    end = break_point

            chunk_content = content[start:end].strip()

            # Estimate pages for this chunk
            progress = (start + end) / 2 / len(content)
            chunk_start_page = start_page + int(progress * total_pages)
            chunk_end_page = min(chunk_start_page + 2, end_page)

            chunks.append((chunk_content, chunk_start_page, chunk_end_page))

            start = end - overlap

        return chunks

    def _create_metadata_header(
        self,
        filing: Filing,
        page_start: int,
        page_end: int,
        total_pages: int,
        section_type: str | None = None,
    ) -> str:
        """Create document context header to prepend to chunks."""
        from podstock.filings.models import FilingType

        filing_type_display = {
            FilingType.ANNUAL_REPORT: "Annual Report (10-K)",
            FilingType.QUARTERLY_REPORT: "Quarterly Report (10-Q)",
            FilingType.INTERIM_REPORT: "Interim Report",
            FilingType.CURRENT_REPORT: "Current Report (8-K)",
        }.get(filing.filing_type, filing.filing_type.value)

        header = f"""[DOCUMENT CONTEXT]
Company: {filing.company_id}
Filing: {filing_type_display}
Fiscal Year: {filing.fiscal_year}"""

        if filing.fiscal_quarter:
            header += f" Q{filing.fiscal_quarter}"

        header += f"""
Period End: {filing.period_end_date.strftime('%Y-%m-%d') if filing.period_end_date else 'N/A'}

[CURRENT LOCATION: Pages {page_start}-{page_end} of {total_pages}]"""

        if section_type:
            section_display = section_type.replace("_", " ").title()
            header += f"\n[SECTION: {section_display}]"

        header += "\n\n---\n\n"
        return header

    def _generate_chunk_id(self, filing_id: str, index: int) -> str:
        """Generate a unique chunk ID."""
        return f"{filing_id}-chunk-{index:03d}"

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token count estimation.

        Uses the approximation that 1 token ≈ 4 characters for English text.
        """
        return len(text) // 4
