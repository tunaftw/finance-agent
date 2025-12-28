"""Base class for filings API clients.

Defines the abstract interface that all filing source clients must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from podstock.filings.models import Company, Filing, FinancialMetrics, FilingType


class FilingsClient(ABC):
    """Abstract base class for filings API clients.

    All filing source clients (EDGAR, manual PDF, etc.) should inherit
    from this class and implement the required methods.

    Example:
        >>> class EdgarClient(FilingsClient):
        ...     @property
        ...     def source_name(self) -> str:
        ...         return "SEC EDGAR"
        ...
        ...     def get_company(self, identifier: str) -> Company | None:
        ...         # Implementation
        ...         pass
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable name of this data source."""
        pass

    @abstractmethod
    def get_company(self, identifier: str) -> Company | None:
        """Look up a company by ticker or other identifier.

        Args:
            identifier: Ticker symbol, CIK, or other identifier.

        Returns:
            Company object if found, None otherwise.
        """
        pass

    @abstractmethod
    def get_filings(
        self,
        company_id: str,
        filing_types: list[FilingType] | None = None,
        limit: int = 5,
    ) -> list[Filing]:
        """Get available filings for a company.

        Args:
            company_id: Company identifier (our internal ID).
            filing_types: Filter by filing types. None = all types.
            limit: Maximum number of filings to return.

        Returns:
            List of Filing objects (without content downloaded).
        """
        pass

    @abstractmethod
    def download_filing(
        self,
        filing: Filing,
        output_dir: Path,
    ) -> Path:
        """Download a filing's content.

        Args:
            filing: The Filing to download.
            output_dir: Directory to save the file.

        Returns:
            Path to the downloaded file.

        Raises:
            FilingsError: If download fails.
        """
        pass

    def get_structured_data(
        self,
        filing: Filing,
    ) -> FinancialMetrics | None:
        """Extract structured financial data (if available).

        Some sources (like EDGAR with XBRL) provide structured data
        that can be extracted without LLM parsing.

        Args:
            filing: The Filing to extract data from.

        Returns:
            FinancialMetrics if structured data available, None otherwise.
        """
        # Default implementation returns None
        # Subclasses with structured data access should override
        return None

    def supports_structured_data(self) -> bool:
        """Check if this client supports structured data extraction.

        Returns:
            True if get_structured_data() is implemented.
        """
        return False
