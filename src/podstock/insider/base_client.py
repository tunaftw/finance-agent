"""Abstract base class for market-specific insider data clients.

Each market (US, Sweden, Norway, etc.) implements this interface
to provide a unified way to fetch insider transaction data.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from podstock.insider.models import InsiderReport


class InsiderClient(ABC):
    """Base class for market-specific insider data clients.

    Subclasses must implement:
        - market_code: The market identifier (e.g., "US", "SE")
        - supported_suffixes: Ticker suffixes this client handles
        - get_transactions: Fetch transactions for a ticker

    Example:
        >>> class SECClient(InsiderClient):
        ...     market_code = "US"
        ...     supported_suffixes = []
        ...
        ...     async def get_transactions(self, ticker, days=90):
        ...         # Fetch from SEC EDGAR
        ...         pass
    """

    @property
    @abstractmethod
    def market_code(self) -> str:
        """Market identifier (e.g., 'US', 'SE', 'NO')."""
        ...

    @property
    @abstractmethod
    def supported_suffixes(self) -> list[str]:
        """Ticker suffixes this client handles.

        Empty list means no suffix (US-style tickers like AAPL).
        Non-empty means specific suffixes (e.g., ['.ST', '.NGM']).
        """
        ...

    @abstractmethod
    async def get_transactions(
        self,
        ticker: str,
        days: int = 90,
    ) -> InsiderReport:
        """Fetch insider transactions for a ticker.

        Args:
            ticker: Stock ticker symbol.
            days: Number of days of history to fetch.

        Returns:
            InsiderReport with transactions.

        Raises:
            TickerNotFoundError: If ticker cannot be resolved.
            RateLimitExceededError: If API rate limit hit.
            ParseError: If response cannot be parsed.
        """
        ...

    def supports_ticker(self, ticker: str) -> bool:
        """Check if this client handles the given ticker.

        Args:
            ticker: Stock ticker symbol to check.

        Returns:
            True if this client can handle the ticker.
        """
        ticker_upper = ticker.upper()

        if not self.supported_suffixes:
            # US-style: no dot in ticker
            return "." not in ticker_upper

        # Check for matching suffix
        return any(
            ticker_upper.endswith(suffix.upper())
            for suffix in self.supported_suffixes
        )
