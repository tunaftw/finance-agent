"""PDF-based filings client for manual imports.

This client handles locally stored PDF files, typically for:
- Swedish company annual reports (downloaded manually)
- Any company not covered by SEC EDGAR
- Historical reports from company websites
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from podstock.filings.clients.base import FilingsClient
from podstock.filings.exceptions import FilingNotFoundError, FilingsError
from podstock.filings.models import (
    Company,
    Filing,
    FilingSource,
    FilingType,
    Market,
)

if TYPE_CHECKING:
    pass


class PDFClient(FilingsClient):
    """Client for manually imported PDF filings.

    This client manages locally stored PDF files. It doesn't fetch from
    external sources but provides a consistent interface for working with
    manually downloaded reports.

    Example:
        >>> client = PDFClient(data_dir / "filings" / "raw")
        >>> filing = client.import_pdf(
        ...     pdf_path="/path/to/EVO_AR_2023.pdf",
        ...     company_id="evolution-gaming",
        ...     filing_type=FilingType.ANNUAL_REPORT,
        ...     fiscal_year=2023
        ... )
    """

    def __init__(self, filings_dir: Path):
        """Initialize the PDF client.

        Args:
            filings_dir: Base directory for storing PDF files.
        """
        self.filings_dir = Path(filings_dir)
        self.filings_dir.mkdir(parents=True, exist_ok=True)

    @property
    def source_name(self) -> str:
        """Human-readable name of this data source."""
        return "Manual PDF Import"

    def get_company(self, identifier: str) -> Company | None:
        """PDF client doesn't lookup companies.

        Companies should be created manually for PDF imports.

        Returns:
            Always None - use create_company() instead.
        """
        return None

    def create_company(
        self,
        name: str,
        ticker: str | None = None,
        market: Market = Market.SWEDEN,
        org_number: str | None = None,
    ) -> Company:
        """Create a new company for PDF imports.

        Args:
            name: Full company name.
            ticker: Stock ticker symbol.
            market: Market/region.
            org_number: Swedish organization number.

        Returns:
            New Company object.
        """
        company_id = Company.generate_id(name)
        return Company(
            id=company_id,
            name=name,
            ticker=ticker,
            market=market,
            org_number=org_number,
        )

    def get_filings(
        self,
        company_id: str,
        filing_types: list[FilingType] | None = None,
        limit: int = 10,
    ) -> list[Filing]:
        """Get existing local filings for a company.

        Args:
            company_id: Our internal company ID.
            filing_types: Filter by filing types. None = all types.
            limit: Maximum number of filings to return.

        Returns:
            List of Filing objects for locally stored PDFs.
        """
        company_dir = self.filings_dir / company_id
        if not company_dir.exists():
            return []

        filings = []
        for pdf_path in company_dir.glob("*.pdf"):
            # Try to parse filing info from filename
            filing = self._parse_filename(pdf_path, company_id)
            if filing:
                if filing_types is None or filing.filing_type in filing_types:
                    filings.append(filing)

        # Sort by fiscal year descending
        filings.sort(key=lambda f: (f.fiscal_year, f.fiscal_quarter or 0), reverse=True)
        return filings[:limit]

    def _parse_filename(self, pdf_path: Path, company_id: str) -> Filing | None:
        """Parse filing info from filename.

        Expected format: {type}-{year}[-q{quarter}].pdf
        Examples: annual-2023.pdf, quarterly-2024-q1.pdf
        """
        stem = pdf_path.stem.lower()

        # Try to extract type and year
        if "annual" in stem or "10-k" in stem or "arsredovisning" in stem:
            filing_type = FilingType.ANNUAL_REPORT
        elif "quarterly" in stem or "10-q" in stem or "kvartalsrapport" in stem:
            filing_type = FilingType.QUARTERLY_REPORT
        elif "interim" in stem:
            filing_type = FilingType.INTERIM_REPORT
        else:
            filing_type = FilingType.OTHER

        # Extract year
        import re

        year_match = re.search(r"20[0-9]{2}", stem)
        if not year_match:
            return None
        fiscal_year = int(year_match.group())

        # Extract quarter
        quarter_match = re.search(r"q([1-4])", stem)
        fiscal_quarter = int(quarter_match.group(1)) if quarter_match else None

        filing_id = Filing.generate_id(company_id, filing_type, fiscal_year, fiscal_quarter)

        return Filing(
            id=filing_id,
            company_id=company_id,
            filing_type=filing_type,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
            filing_date=datetime.fromtimestamp(pdf_path.stat().st_mtime),
            source=FilingSource.MANUAL_PDF,
            local_path=str(pdf_path.relative_to(self.filings_dir)),
        )

    def import_pdf(
        self,
        pdf_path: str | Path,
        company_id: str,
        filing_type: FilingType,
        fiscal_year: int,
        fiscal_quarter: int | None = None,
        filing_date: datetime | None = None,
        period_end_date: datetime | None = None,
    ) -> Filing:
        """Import a PDF file for a company.

        Args:
            pdf_path: Path to the source PDF file.
            company_id: Company ID this filing belongs to.
            filing_type: Type of filing (annual, quarterly, etc.).
            fiscal_year: Fiscal year of the report.
            fiscal_quarter: Quarter number for quarterly reports.
            filing_date: When the report was filed/published.
            period_end_date: End date of the reporting period.

        Returns:
            Filing object for the imported PDF.

        Raises:
            FileNotFoundError: If the source PDF doesn't exist.
        """
        from podstock.filings.pdf.parser import PDFParser

        source_path = Path(pdf_path)
        if not source_path.exists():
            raise FileNotFoundError(f"PDF not found: {source_path}")

        # Create company directory
        company_dir = self.filings_dir / company_id
        company_dir.mkdir(parents=True, exist_ok=True)

        # Generate filing ID and filename
        filing_id = Filing.generate_id(company_id, filing_type, fiscal_year, fiscal_quarter)
        filename = f"{filing_type.value}-{fiscal_year}"
        if fiscal_quarter:
            filename += f"-q{fiscal_quarter}"
        filename += ".pdf"

        dest_path = company_dir / filename

        # Copy the file
        shutil.copy2(source_path, dest_path)

        # Get page count
        parser = PDFParser()
        page_count = parser.get_page_count(dest_path)

        # Detect language from content
        try:
            content = parser.to_markdown(dest_path)[:2000]
            language = self._detect_language(content)
        except Exception:
            language = "en"

        return Filing(
            id=filing_id,
            company_id=company_id,
            filing_type=filing_type,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
            filing_date=filing_date or datetime.now(),
            period_end_date=period_end_date,
            source=FilingSource.MANUAL_PDF,
            local_path=str(dest_path.relative_to(self.filings_dir)),
            page_count=page_count,
            language=language,
        )

    def download_filing(
        self,
        filing: Filing,
        output_dir: Path,
    ) -> Path:
        """Get the path to a filing's PDF.

        For PDF client, this just returns the existing path since
        files are already local.

        Args:
            filing: The Filing to get.
            output_dir: Ignored for PDF client.

        Returns:
            Path to the PDF file.
        """
        if not filing.local_path:
            raise FilingNotFoundError(filing.id, "No local path stored")

        pdf_path = self.filings_dir / filing.local_path
        if not pdf_path.exists():
            raise FilingNotFoundError(filing.id, f"PDF not found: {pdf_path}")

        return pdf_path

    def get_pdf_path(self, filing: Filing) -> Path:
        """Get the absolute path to a filing's PDF.

        Args:
            filing: The Filing object.

        Returns:
            Absolute path to the PDF file.

        Raises:
            FilingNotFoundError: If the PDF doesn't exist.
        """
        if not filing.local_path:
            raise FilingNotFoundError(filing.id, "No local path stored")

        pdf_path = self.filings_dir / filing.local_path
        if not pdf_path.exists():
            raise FilingNotFoundError(filing.id, f"PDF not found: {pdf_path}")

        return pdf_path

    def _detect_language(self, text: str) -> str:
        """Simple language detection based on common words.

        Args:
            text: Sample text to analyze.

        Returns:
            Language code ('sv' for Swedish, 'en' for English).
        """
        text_lower = text.lower()

        # Swedish indicators
        swedish_words = [
            "och",
            "att",
            "som",
            "för",
            "är",
            "med",
            "har",
            "det",
            "på",
            "från",
            "verksamhet",
            "bolag",
            "aktie",
            "årsredovisning",
            "resultat",
            "tillgångar",
        ]

        swedish_count = sum(1 for word in swedish_words if f" {word} " in f" {text_lower} ")

        if swedish_count >= 5:
            return "sv"
        return "en"

    def delete_filing(self, filing: Filing) -> None:
        """Delete a filing's PDF file.

        Args:
            filing: The Filing to delete.
        """
        if filing.local_path:
            pdf_path = self.filings_dir / filing.local_path
            if pdf_path.exists():
                pdf_path.unlink()
