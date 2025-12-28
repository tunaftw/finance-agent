"""CoinGecko adapter for the unified prices interface.

This module wraps the existing crypto.CoinGeckoClient to conform
to the PriceClient interface for unified price tracking.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from podstock.prices.clients.base import PriceClient
from podstock.prices.models import PriceSnapshot

if TYPE_CHECKING:
    from podstock.crypto.coingecko import CoinGeckoClient


class CoinGeckoAdapter(PriceClient):
    """Adapter wrapping CoinGeckoClient to PriceClient interface.

    This adapter allows the unified price tracking system to use
    the existing CoinGecko client for crypto assets.

    Example:
        >>> from podstock.crypto.coingecko import CoinGeckoClient
        >>> base_client = CoinGeckoClient()
        >>> adapter = CoinGeckoAdapter(base_client)
        >>> price = adapter.get_current_price("BTC")
    """

    def __init__(
        self,
        client: "CoinGeckoClient | None" = None,
        default_currency: str = "USD",
    ):
        """Initialize the adapter.

        Args:
            client: Existing CoinGeckoClient instance, or None to create one.
            default_currency: Default currency for prices (USD or SEK).
        """
        if client is None:
            from podstock.crypto.coingecko import CoinGeckoClient

            client = CoinGeckoClient()

        self._client = client
        self.default_currency = default_currency.lower()

    def get_current_price(self, symbol: str) -> PriceSnapshot | None:
        """Get current price for a crypto symbol.

        Args:
            symbol: Crypto symbol (BTC, ETH, etc.).

        Returns:
            PriceSnapshot with current price or None.
        """
        price = self._client.get_current_price(symbol, self.default_currency)

        if price is None:
            return None

        return PriceSnapshot(
            symbol=symbol.upper(),
            price=price,
            currency=self.default_currency.upper(),
            timestamp=datetime.now(),
            source="coingecko",
        )

    def get_historical_price(
        self, symbol: str, date: datetime
    ) -> PriceSnapshot | None:
        """Get price at a specific historical date.

        Args:
            symbol: Crypto symbol.
            date: Target date.

        Returns:
            PriceSnapshot with price at that date or None.
        """
        price = self._client.get_historical_price(symbol, date, self.default_currency)

        if price is None:
            return None

        return PriceSnapshot(
            symbol=symbol.upper(),
            price=price,
            currency=self.default_currency.upper(),
            timestamp=date,
            source="coingecko",
        )

    def get_price_range(
        self, symbol: str, start: datetime, end: datetime
    ) -> list[PriceSnapshot]:
        """Get prices over a date range.

        Args:
            symbol: Crypto symbol.
            start: Start date.
            end: End date.

        Returns:
            List of PriceSnapshot objects.
        """
        # Calculate days from end to now
        days = (datetime.now() - start).days + 1
        days = max(1, min(days, 365))  # CoinGecko limits to 365 days

        price_tuples = self._client.get_price_range(
            symbol, days=days, currency=self.default_currency
        )

        snapshots: list[PriceSnapshot] = []
        for dt, price in price_tuples:
            # Filter to requested range
            if start <= dt <= end:
                snapshots.append(
                    PriceSnapshot(
                        symbol=symbol.upper(),
                        price=price,
                        currency=self.default_currency.upper(),
                        timestamp=dt,
                        source="coingecko",
                    )
                )

        return snapshots

    @property
    def source_name(self) -> str:
        """Return source identifier.

        Returns:
            "coingecko"
        """
        return "coingecko"

    def is_valid_symbol(self, symbol: str) -> bool:
        """Check if a crypto symbol is valid.

        Args:
            symbol: The crypto symbol.

        Returns:
            True if symbol is known.
        """
        return self._client.get_coin_id(symbol) is not None
