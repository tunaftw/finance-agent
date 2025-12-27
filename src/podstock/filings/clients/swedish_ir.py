"""Swedish IR page client for downloading financial reports.

This client scrapes company investor relations pages to find and
download financial reports (årsredovisningar, kvartalsrapporter).
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from podstock.filings.clients.base import FilingsClient
from podstock.filings.exceptions import CompanyNotFoundError, FilingsError
from podstock.filings.models import (
    Company,
    Filing,
    FilingSource,
    FilingType,
    Market,
)
from podstock.filings.swedish.ir_registry import IRRegistry, MarketSegment
from podstock.filings.swedish.ir_scraper import IRScraper

if TYPE_CHECKING:
    from podstock.filings.models import FinancialMetrics

logger = logging.getLogger(__name__)


class SwedishIRClient(FilingsClient):
    """Client for Swedish company filings via IR page scraping.

    This client uses a registry of known Swedish companies and their
    IR page URLs to find and download financial reports.

    Example:
        >>> client = SwedishIRClient()
        >>> company = client.get_company("evolution")
        >>> filings = client.get_filings(company.id, limit=5)
        >>> for filing in filings:
        ...     print(f"{filing.filing_type}: {filing.fiscal_year}")
    """

    def __init__(
        self,
        registry: IRRegistry | None = None,
        scraper: IRScraper | None = None,
    ):
        """Initialize the Swedish IR client.

        Args:
            registry: Optional custom IR registry.
            scraper: Optional custom scraper instance.
        """
        self.registry = registry or IRRegistry()
        self.scraper = scraper or IRScraper()

    @property
    def source_name(self) -> str:
        """Human-readable name of this data source."""
        return "Swedish IR Pages"

    def get_company(self, identifier: str) -> Company | None:
        """Look up a company by name, ticker, or ID.

        Args:
            identifier: Company name, ticker, or ID.

        Returns:
            Company object if found in registry, None otherwise.
        """
        # Try exact ID match first
        info = self.registry.get(identifier)

        # Try ticker match
        if not info:
            info = self.registry.get_by_ticker(identifier)

        # Try search
        if not info:
            results = self.registry.search(identifier)
            if results:
                info = results[0]

        if not info:
            return None

        return Company(
            id=info.id,
            name=info.name,
            ticker=info.ticker,
            market=Market.SWEDEN,
        )

    def get_filings(
        self,
        company_id: str,
        filing_types: list[FilingType] | None = None,
        limit: int = 5,
        **kwargs,
    ) -> list[Filing]:
        """Get available filings for a company by scraping IR page.

        Args:
            company_id: Company ID (must exist in registry).
            filing_types: Filter by filing types. None = annual + quarterly.
            limit: Maximum number of filings to return.

        Returns:
            List of Filing objects.

        Raises:
            CompanyNotFoundError: If company not in registry.
        """
        info = self.registry.get(company_id)
        if not info:
            raise CompanyNotFoundError(company_id, "sweden", "Company not in IR registry")

        # Default to annual and quarterly
        if filing_types is None:
            filing_types = [FilingType.ANNUAL_REPORT, FilingType.QUARTERLY_REPORT]

        try:
            # Scrape IR page to find reports
            found_reports = self.scraper.find_reports(info, limit=limit * 2)

            filings = []
            for report in found_reports:
                # Filter by type
                if report.filing_type not in filing_types:
                    continue

                filing_id = Filing.generate_id(
                    company_id,
                    report.filing_type,
                    report.year,
                    report.quarter,
                )

                filing = Filing(
                    id=filing_id,
                    company_id=company_id,
                    filing_type=report.filing_type,
                    fiscal_year=report.year,
                    fiscal_quarter=report.quarter,
                    filing_date=datetime(report.year, 12, 31),  # Approximate
                    source=FilingSource.COMPANY_WEBSITE,
                    source_url=report.url,
                    language=report.language,
                )
                filings.append(filing)

            return filings[:limit]

        except Exception as e:
            logger.error(f"Failed to get filings for {company_id}: {e}")
            raise FilingsError(f"Failed to scrape filings for {company_id}: {e}") from e

    def download_filing(
        self,
        filing: Filing,
        output_dir: Path,
    ) -> Path:
        """Download a filing's PDF content.

        Args:
            filing: The Filing to download.
            output_dir: Directory to save the file.

        Returns:
            Path to the downloaded file.
        """
        if not filing.source_url:
            raise FilingsError(f"No source URL for filing {filing.id}")

        output_dir = Path(output_dir)
        company_dir = output_dir / filing.company_id
        company_dir.mkdir(parents=True, exist_ok=True)

        # Generate standardized filename
        filename = filing.generate_filename()
        output_path = company_dir / filename

        # Download using scraper's session
        try:
            response = self.scraper.session.get(
                filing.source_url,
                timeout=self.scraper.timeout,
                stream=True,
            )
            response.raise_for_status()

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Downloaded: {output_path}")
            return output_path

        except Exception as e:
            raise FilingsError(f"Failed to download filing {filing.id}: {e}") from e

    def get_structured_data(
        self,
        filing: Filing,
    ) -> FinancialMetrics | None:
        """Swedish IR pages don't provide structured data."""
        return None

    def supports_structured_data(self) -> bool:
        """Swedish IR pages don't provide structured data."""
        return False

    def list_available_companies(
        self,
        segment: MarketSegment | None = None,
    ) -> list[Company]:
        """List companies available in the registry.

        Args:
            segment: Filter by market segment.

        Returns:
            List of available companies.
        """
        if segment:
            infos = self.registry.list_by_segment(segment)
        else:
            infos = self.registry.list_all()

        return [
            Company(
                id=info.id,
                name=info.name,
                ticker=info.ticker,
                market=Market.SWEDEN,
            )
            for info in infos
        ]
