"""Table extraction from financial PDFs using pdfplumber.

pdfplumber provides high-precision table extraction which is crucial
for accurately capturing financial data from income statements,
balance sheets, and cash flow statements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ExtractedTable:
    """A table extracted from a PDF.

    Attributes:
        page_number: 1-based page number where table was found.
        table_index: Index of table on the page (0-based).
        headers: Column headers (first row).
        rows: Data rows (list of lists).
        raw_data: Original pdfplumber output.
        bbox: Bounding box coordinates (x0, y0, x1, y1).
    """

    page_number: int
    table_index: int
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    raw_data: list[list[Any]] = field(default_factory=list)
    bbox: tuple[float, float, float, float] | None = None

    @property
    def row_count(self) -> int:
        """Number of data rows (excluding header)."""
        return len(self.rows)

    @property
    def column_count(self) -> int:
        """Number of columns."""
        return len(self.headers) if self.headers else (len(self.rows[0]) if self.rows else 0)

    def to_markdown(self) -> str:
        """Convert table to Markdown format."""
        if not self.headers and not self.rows:
            return ""

        lines = []

        # Header row
        if self.headers:
            lines.append("| " + " | ".join(str(h) for h in self.headers) + " |")
            lines.append("|" + "|".join("---" for _ in self.headers) + "|")
        elif self.rows:
            # Use first row as header if no explicit headers
            first_row = self.rows[0]
            lines.append("| " + " | ".join(str(c) for c in first_row) + " |")
            lines.append("|" + "|".join("---" for _ in first_row) + "|")
            self.rows = self.rows[1:]

        # Data rows
        for row in self.rows:
            lines.append("| " + " | ".join(str(c) if c else "" for c in row) + " |")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "page_number": self.page_number,
            "table_index": self.table_index,
            "headers": self.headers,
            "rows": self.rows,
            "row_count": self.row_count,
            "column_count": self.column_count,
        }


class TableExtractor:
    """Extract tables from PDFs using pdfplumber.

    pdfplumber is specifically designed for extracting structured data
    from PDFs and provides better table detection than general-purpose
    PDF libraries.

    Example:
        >>> extractor = TableExtractor()
        >>> tables = extractor.extract_all_tables("/path/to/annual_report.pdf")
        >>> for table in tables:
        ...     print(f"Page {table.page_number}: {table.row_count} rows")
    """

    def __init__(
        self,
        *,
        min_rows: int = 2,
        min_columns: int = 2,
        vertical_strategy: str = "lines",
        horizontal_strategy: str = "lines",
    ):
        """Initialize the table extractor.

        Args:
            min_rows: Minimum rows for a valid table.
            min_columns: Minimum columns for a valid table.
            vertical_strategy: pdfplumber vertical line detection strategy.
            horizontal_strategy: pdfplumber horizontal line detection strategy.
        """
        self.min_rows = min_rows
        self.min_columns = min_columns
        self.table_settings = {
            "vertical_strategy": vertical_strategy,
            "horizontal_strategy": horizontal_strategy,
        }
        self._pdfplumber = None

    def _ensure_pdfplumber(self):
        """Lazy import pdfplumber."""
        if self._pdfplumber is None:
            try:
                import pdfplumber

                self._pdfplumber = pdfplumber
            except ImportError as e:
                raise ImportError(
                    "pdfplumber is required for table extraction. "
                    "Install with: pip install pdfplumber"
                ) from e

    def extract_all_tables(
        self,
        pdf_path: str | Path,
        pages: list[int] | None = None,
    ) -> list[ExtractedTable]:
        """Extract all tables from a PDF.

        Args:
            pdf_path: Path to the PDF file.
            pages: Optional list of page numbers (1-based) to process.
                   If None, processes all pages.

        Returns:
            List of ExtractedTable objects.

        Raises:
            FileNotFoundError: If the PDF doesn't exist.
        """
        self._ensure_pdfplumber()

        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        tables = []

        with self._pdfplumber.open(str(path)) as pdf:
            pages_to_process = pdf.pages
            if pages:
                # Filter to specified pages (convert to 0-based index)
                pages_to_process = [pdf.pages[p - 1] for p in pages if 0 < p <= len(pdf.pages)]

            for page in pages_to_process:
                page_tables = self._extract_tables_from_page(page)
                tables.extend(page_tables)

        return tables

    def extract_tables_from_pages(
        self,
        pdf_path: str | Path,
        start_page: int,
        end_page: int,
    ) -> list[ExtractedTable]:
        """Extract tables from a range of pages.

        Args:
            pdf_path: Path to the PDF file.
            start_page: Start page (1-based, inclusive).
            end_page: End page (1-based, inclusive).

        Returns:
            List of ExtractedTable objects.
        """
        pages = list(range(start_page, end_page + 1))
        return self.extract_all_tables(pdf_path, pages)

    def _extract_tables_from_page(self, page) -> list[ExtractedTable]:
        """Extract tables from a single pdfplumber page object."""
        tables = []
        page_number = page.page_number  # 1-based

        try:
            page_tables = page.extract_tables(self.table_settings)
        except Exception:
            # Some pages may fail to extract tables
            return []

        for idx, raw_table in enumerate(page_tables):
            if not raw_table:
                continue

            # Filter empty rows
            raw_table = [row for row in raw_table if any(cell for cell in row)]

            if len(raw_table) < self.min_rows:
                continue

            # Check column count
            max_cols = max(len(row) for row in raw_table) if raw_table else 0
            if max_cols < self.min_columns:
                continue

            # Clean cell values
            cleaned = []
            for row in raw_table:
                cleaned_row = []
                for cell in row:
                    if cell is None:
                        cleaned_row.append("")
                    else:
                        # Clean whitespace and normalize
                        cleaned_cell = str(cell).strip().replace("\n", " ")
                        cleaned_row.append(cleaned_cell)
                cleaned.append(cleaned_row)

            # First row is typically headers
            headers = cleaned[0] if cleaned else []
            rows = cleaned[1:] if len(cleaned) > 1 else []

            table = ExtractedTable(
                page_number=page_number,
                table_index=idx,
                headers=headers,
                rows=rows,
                raw_data=raw_table,
            )
            tables.append(table)

        return tables

    def find_financial_tables(
        self,
        pdf_path: str | Path,
    ) -> dict[str, list[ExtractedTable]]:
        """Find and categorize financial statement tables.

        Attempts to identify:
        - Income Statement / Resultaträkning
        - Balance Sheet / Balansräkning
        - Cash Flow Statement / Kassaflödesanalys

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Dictionary mapping statement type to list of tables.
        """
        all_tables = self.extract_all_tables(pdf_path)

        categorized = {
            "income_statement": [],
            "balance_sheet": [],
            "cash_flow": [],
            "other": [],
        }

        # Keywords for each statement type
        income_keywords = [
            "revenue",
            "sales",
            "net income",
            "operating income",
            "gross profit",
            "omsättning",
            "nettoomsättning",
            "rörelseresultat",
            "årets resultat",
        ]

        balance_keywords = [
            "assets",
            "liabilities",
            "equity",
            "total assets",
            "current assets",
            "tillgångar",
            "skulder",
            "eget kapital",
            "balansomslutning",
        ]

        cashflow_keywords = [
            "cash flow",
            "operating activities",
            "investing activities",
            "financing activities",
            "kassaflöde",
            "löpande verksamhet",
        ]

        for table in all_tables:
            # Check all text in headers and first few rows
            table_text = " ".join(table.headers).lower()
            for row in table.rows[:3]:
                table_text += " " + " ".join(str(c) for c in row).lower()

            if any(kw in table_text for kw in income_keywords):
                categorized["income_statement"].append(table)
            elif any(kw in table_text for kw in balance_keywords):
                categorized["balance_sheet"].append(table)
            elif any(kw in table_text for kw in cashflow_keywords):
                categorized["cash_flow"].append(table)
            else:
                categorized["other"].append(table)

        return categorized

    def tables_to_markdown(self, tables: list[ExtractedTable]) -> str:
        """Convert multiple tables to a single Markdown string.

        Args:
            tables: List of extracted tables.

        Returns:
            Markdown string with all tables.
        """
        parts = []
        for table in tables:
            parts.append(f"### Table from Page {table.page_number}")
            parts.append("")
            parts.append(table.to_markdown())
            parts.append("")

        return "\n".join(parts)
