"""Router for directing ticker lookups to appropriate market clients.

The router detects which market a ticker belongs to based on its
suffix and returns the appropriate client for that market.
"""

from __future__ import annotations

from podstock.insider.base_client import InsiderClient
from podstock.insider.exceptions import SourceUnavailableError

# Mapping of ticker suffixes to market codes
SUFFIX_TO_MARKET: dict[str, str] = {
    ".ST": "SE",  # Stockholm (Nasdaq Stockholm)
    ".NGM": "SE",  # Nordic Growth Market (Sweden)
    ".OL": "NO",  # Oslo Bors
    ".CO": "DK",  # Copenhagen (Nasdaq Copenhagen)
    ".HE": "FI",  # Helsinki (Nasdaq Helsinki)
}


class InsiderRouter:
    """Routes ticker lookups to appropriate market-specific clients.

    The router maintains a registry of clients and determines which
    one to use based on the ticker's suffix.

    Example:
        >>> router = InsiderRouter()
        >>> router.detect_market("AAPL")
        'US'
        >>> router.detect_market("EVO.ST")
        'SE'
    """

    def __init__(self) -> None:
        """Initialize the router with registered clients."""
        self._clients: dict[str, InsiderClient] = {}

    def register_client(self, client: InsiderClient) -> None:
        """Register a client for its market.

        Args:
            client: The client instance to register.
        """
        self._clients[client.market_code] = client

    def detect_market(self, ticker: str) -> str | None:
        """Detect which market a ticker belongs to.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Market code (US, SE, NO, etc.) or None if unknown.
        """
        ticker_upper = ticker.upper()

        # Check for known suffixes
        for suffix, market in SUFFIX_TO_MARKET.items():
            if ticker_upper.endswith(suffix.upper()):
                return market

        # No suffix = US market
        if "." not in ticker_upper:
            return "US"

        return None

    def get_client(self, ticker: str) -> InsiderClient:
        """Get the appropriate client for a ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            The client that handles this ticker's market.

        Raises:
            SourceUnavailableError: If market not supported or no client registered.
        """
        market = self.detect_market(ticker)

        if market is None:
            # Extract suffix for error message
            suffix = "." + ticker.split(".")[-1] if "." in ticker else "unknown"
            raise SourceUnavailableError(f"unknown ({suffix})")

        if market not in self._clients:
            raise SourceUnavailableError(market)

        return self._clients[market]

    @property
    def supported_markets(self) -> list[str]:
        """List of markets with registered clients."""
        return list(self._clients.keys())
