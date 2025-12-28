"""SEC EDGAR API client using EdgarTools.

This module provides access to US SEC filings through the EDGAR database.
EdgarTools is used for company lookup and filing retrieval, while
secfsdstools can be used for XBRL data extraction.

Note: SEC requires a user agent for API access. Set the EDGAR_USER_AGENT
environment variable or pass it to the constructor.
"""

from __future__ import annotations

import os
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
    FinancialMetrics,
    Market,
)

if TYPE_CHECKING:
    pass


# Mapping from SEC form types to our FilingType enum
FORM_TYPE_MAP = {
    "10-K": FilingType.ANNUAL_REPORT,
    "10-K/A": FilingType.ANNUAL_REPORT,
    "10-Q": FilingType.QUARTERLY_REPORT,
    "10-Q/A": FilingType.QUARTERLY_REPORT,
    "8-K": FilingType.CURRENT_REPORT,
    "8-K/A": FilingType.CURRENT_REPORT,
    "S-1": FilingType.PROSPECTUS,
    "S-1/A": FilingType.PROSPECTUS,
}


class EdgarClient(FilingsClient):
    """SEC EDGAR API client via EdgarTools.

    Provides access to US company filings from the SEC EDGAR database.
    Supports structured XBRL data extraction for financial statements.

    Example:
        >>> client = EdgarClient()
        >>> company = client.get_company("AAPL")
        >>> filings = client.get_filings(company.id, limit=3)
        >>> for filing in filings:
        ...     print(f"{filing.filing_type}: {filing.fiscal_year}")
    """

    def __init__(
        self,
        user_agent: str | None = None,
    ):
        """Initialize the EDGAR client.

        Args:
            user_agent: User agent string for SEC API.
                       Format: "Company Name email@example.com"
                       Falls back to EDGAR_USER_AGENT env var.
        """
        self.user_agent = user_agent or os.getenv(
            "EDGAR_USER_AGENT",
            "PodStock/1.0 podstock@example.com",
        )
        self._edgartools = None

    def _ensure_edgartools(self):
        """Lazy import edgar (edgartools package) and configure."""
        if self._edgartools is None:
            try:
                import edgar
                from edgar import set_identity

                # Set the identity for SEC API compliance
                set_identity(self.user_agent)
                self._edgartools = edgar
            except ImportError as e:
                raise ImportError(
                    "edgartools is required for SEC EDGAR access. "
                    "Install with: pip install edgartools"
                ) from e

    @property
    def source_name(self) -> str:
        """Human-readable name of this data source."""
        return "SEC EDGAR"

    def get_company(self, identifier: str) -> Company | None:
        """Look up a company by ticker or CIK.

        Args:
            identifier: Stock ticker (e.g., "AAPL") or CIK number.

        Returns:
            Company object if found, None otherwise.
        """
        self._ensure_edgartools()

        try:
            from edgar import Company as EdgarCompany

            edgar_company = EdgarCompany(identifier)

            # Generate our internal ID
            company_id = Company.generate_id(edgar_company.name)

            return Company(
                id=company_id,
                name=edgar_company.name,
                ticker=edgar_company.tickers[0] if edgar_company.tickers else None,
                market=Market.US,
                cik=str(edgar_company.cik).zfill(10),
            )
        except Exception:
            return None

    def get_filings(
        self,
        company_id: str,
        filing_types: list[FilingType] | None = None,
        limit: int = 5,
        cik: str | None = None,
        ticker: str | None = None,
    ) -> list[Filing]:
        """Get available filings for a company.

        Args:
            company_id: Our internal company ID.
            filing_types: Filter by filing types. None = annual + quarterly.
            limit: Maximum number of filings to return.
            cik: SEC CIK number (if known).
            ticker: Stock ticker (if known).

        Returns:
            List of Filing objects.
        """
        self._ensure_edgartools()

        from edgar import Company as EdgarCompany

        # We need either CIK or ticker to look up the company
        identifier = cik or ticker
        if not identifier:
            raise FilingsError(f"Need CIK or ticker to fetch filings for {company_id}")

        try:
            edgar_company = EdgarCompany(identifier)
        except Exception as e:
            raise CompanyNotFoundError(identifier, "us", str(e)) from e

        # Map our FilingType to SEC form types
        if filing_types is None:
            form_types = ["10-K", "10-Q"]
        else:
            form_types = []
            for ft in filing_types:
                if ft == FilingType.ANNUAL_REPORT:
                    form_types.append("10-K")
                elif ft == FilingType.QUARTERLY_REPORT:
                    form_types.append("10-Q")
                elif ft == FilingType.CURRENT_REPORT:
                    form_types.append("8-K")

        filings = []

        for form_type in form_types:
            try:
                edgar_filings = edgar_company.get_filings(form=form_type)

                # Convert to pandas DataFrame for easier access
                df = edgar_filings.to_pandas()
                if df.empty:
                    continue

                # Take only the most recent filings
                df = df.head(limit)

                for _, row in df.iterrows():
                    filing = self._convert_edgar_row(
                        row,
                        company_id,
                        form_type,
                        edgar_company.cik,
                    )
                    if filing:
                        filings.append(filing)
            except Exception as e:
                # Log but continue with other form types
                import logging
                logging.debug(f"Failed to get {form_type} filings: {e}")
                continue

        # Sort by filing date descending
        filings.sort(key=lambda f: f.filing_date, reverse=True)
        return filings[:limit]

    def _convert_edgar_row(
        self,
        row,
        company_id: str,
        form_type: str,
        cik: str,
    ) -> Filing | None:
        """Convert a pandas row from edgar filings to our Filing model."""
        import pandas as pd

        try:
            filing_type = FORM_TYPE_MAP.get(form_type, FilingType.OTHER)

            # Extract filing date
            filing_date = row.get("filing_date")
            if isinstance(filing_date, str):
                filing_date = datetime.fromisoformat(filing_date)
            elif isinstance(filing_date, pd.Timestamp):
                filing_date = filing_date.to_pydatetime()

            # Try to get period end date (reportDate)
            period_end = row.get("reportDate")
            if period_end:
                if isinstance(period_end, str):
                    period_end = datetime.fromisoformat(period_end)
                elif isinstance(period_end, pd.Timestamp):
                    period_end = period_end.to_pydatetime()

            # Determine fiscal year and quarter
            if period_end:
                fiscal_year = period_end.year
                fiscal_quarter = (period_end.month - 1) // 3 + 1 if filing_type == FilingType.QUARTERLY_REPORT else None
            else:
                fiscal_year = filing_date.year
                fiscal_quarter = None

            filing_id = Filing.generate_id(company_id, filing_type, fiscal_year, fiscal_quarter)

            # Get the filing URL
            accession = row.get("accession_number", "").replace("-", "")
            primary_doc = row.get("primaryDocument", "")
            source_url = None
            if accession and primary_doc:
                source_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{primary_doc}"

            return Filing(
                id=filing_id,
                company_id=company_id,
                filing_type=filing_type,
                fiscal_year=fiscal_year,
                fiscal_quarter=fiscal_quarter,
                filing_date=filing_date,
                period_end_date=period_end,
                source=FilingSource.SEC_EDGAR,
                source_url=source_url,
                language="en",
            )
        except Exception as e:
            import logging
            logging.debug(f"Failed to convert filing row: {e}")
            return None

    def download_filing(
        self,
        filing: Filing,
        output_dir: Path,
    ) -> Path:
        """Download a filing's HTML content.

        Args:
            filing: The Filing to download.
            output_dir: Directory to save the file.

        Returns:
            Path to the downloaded file.
        """
        self._ensure_edgartools()

        import requests

        if not filing.source_url:
            raise FilingsError(f"No source URL for filing {filing.id}")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Determine filename
        filename = f"{filing.id}.html"
        output_path = output_dir / filename

        try:
            response = requests.get(
                filing.source_url,
                headers={"User-Agent": self.user_agent},
                timeout=30,
            )
            response.raise_for_status()

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(response.text)

            return output_path
        except Exception as e:
            raise FilingsError(f"Failed to download filing {filing.id}: {e}") from e

    def get_structured_data(
        self,
        filing: Filing,
    ) -> FinancialMetrics | None:
        """Extract structured financial data via XBRL.

        Uses secfsdstools for XBRL parsing if available.

        Args:
            filing: The Filing to extract data from.

        Returns:
            FinancialMetrics if XBRL data available, None otherwise.
        """
        # Try to use secfsdstools for structured data
        try:
            return self._extract_xbrl_metrics(filing)
        except Exception:
            return None

    def _extract_xbrl_metrics(self, filing: Filing) -> FinancialMetrics | None:
        """Extract metrics from XBRL data using secfsdstools."""
        try:
            from secfsdstools.e_filter.rawfiltering import ReportPeriodRawFilter
            from secfsdstools.e_read.companycollecting import CompanyReportCollector

            # This is a simplified example - full implementation would need
            # to properly query the SEC financial statement data sets
            # which requires downloading and caching the datasets

            # For now, return None and let LLM extraction handle it
            return None

        except ImportError:
            # secfsdstools not installed
            return None
        except Exception:
            return None

    def supports_structured_data(self) -> bool:
        """Check if XBRL extraction is available."""
        try:
            import secfsdstools

            return True
        except ImportError:
            return False
