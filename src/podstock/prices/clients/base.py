"""Abstract base class for price data clients."""

from abc import ABC, abstractmethod
from datetime import datetime

from podstock.prices.models import PriceSnapshot


class PriceClient(ABC):
    """Abstract base class for price data providers.

    All price clients must implement this interface to ensure
    consistent behavior across different data sources.
    """

    @abstractmethod
    def get_current_price(self, symbol: str) -> PriceSnapshot | None:
        """Get current price for a symbol.

        Args:
            symbol: The ticker symbol (e.g., "EVO.ST", "BTC").

        Returns:
            PriceSnapshot with current price or None if unavailable.
        """
        pass

    @abstractmethod
    def get_historical_price(
        self, symbol: str, date: datetime
    ) -> PriceSnapshot | None:
        """Get price at a specific historical date.

        Args:
            symbol: The ticker symbol.
            date: The date to get price for.

        Returns:
            PriceSnapshot with closing price for that date, or None.
        """
        pass

    @abstractmethod
    def get_price_range(
        self, symbol: str, start: datetime, end: datetime
    ) -> list[PriceSnapshot]:
        """Get prices over a date range.

        Args:
            symbol: The ticker symbol.
            start: Start date (inclusive).
            end: End date (inclusive).

        Returns:
            List of PriceSnapshot objects for each trading day.
        """
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return source identifier for PriceSnapshot.

        Returns:
            Source name (e.g., "yahoo", "coingecko").
        """
        pass

    def is_available(self, symbol: str) -> bool:
        """Check if price data is available for a symbol.

        Args:
            symbol: The ticker symbol.

        Returns:
            True if data is available.
        """
        return self.get_current_price(symbol) is not None
