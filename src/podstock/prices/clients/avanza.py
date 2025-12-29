"""Avanza price client using their unofficial public API.

This module provides the AvanzaClient for fetching stock prices from Avanza's
public price-chart API. It's primarily useful for:
- First North stocks that aren't available on Yahoo Finance
- Swedish stocks as a fallback when Yahoo fails

The API does NOT require authentication for public price data.

Features:
- 5 years of OHLC data available
- Rate limiting to avoid being blocked
- orderbookId-based lookups

Example usage::

    from podstock.prices.clients.avanza import AvanzaClient

    client = AvanzaClient()

    # Get current price by orderbookId
    snapshot = client.get_current_price("13477")  # Kopparbergs B
    print(f"Kopparbergs: {snapshot.price} {snapshot.currency}")

    # Get historical price
    from datetime import datetime
    hist = client.get_historical_price("13477", datetime(2024, 6, 15))
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

from podstock.prices.clients.base import PriceClient
from podstock.prices.models import PriceSnapshot


class AvanzaClient(PriceClient):
    """Avanza price client using their public price-chart API.

    Fetches price data from Avanza's undocumented public API.
    No authentication required for public price data.

    Attributes:
        rate_limit_delay: Seconds to wait between requests.
        mapping: Dictionary mapping stock names to orderbookIds.

    Methods
    -------
    get_current_price(orderbook_id)
        Get current price for an orderbookId.
    get_historical_price(orderbook_id, date)
        Get closing price for a specific historical date.
    get_price_range(orderbook_id, start, end)
        Get daily prices over a date range.
    lookup_orderbook_id(stock_name)
        Look up orderbookId from stock name using mapping file.
    """

    BASE_URL = "https://www.avanza.se/_api/price-chart/stock"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    # Map time period names to API values
    TIME_PERIODS = {
        "one_week": "one_week",
        "one_month": "one_month",
        "three_months": "three_months",
        "one_year": "one_year",
        "three_years": "three_years",
        "five_years": "five_years",
    }

    def __init__(
        self,
        rate_limit_delay: float = 0.3,
        mapping_file: Path | str | None = None,
    ):
        """Initialize the Avanza client.

        Args:
            rate_limit_delay: Seconds to wait between API requests.
            mapping_file: Path to JSON file with stock name -> orderbookId mapping.
        """
        self.rate_limit_delay = rate_limit_delay
        self._last_request_time: float = 0.0
        self._price_cache: dict[str, list[dict]] = {}  # orderbookId -> OHLC data

        # Load mapping file
        self.mapping: dict[str, str] = {}
        if mapping_file is None:
            mapping_file = Path("data/prices/avanza_mapping.json")
        if isinstance(mapping_file, str):
            mapping_file = Path(mapping_file)
        if mapping_file.exists():
            with open(mapping_file) as f:
                data = json.load(f)
                self.mapping = data.get("mappings", {})

    def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def _fetch_price_data(self, orderbook_id: str, period: str = "five_years") -> list[dict] | None:
        """Fetch OHLC data from Avanza API.

        Args:
            orderbook_id: Avanza's internal stock ID.
            period: Time period (one_week, one_month, three_months, one_year, three_years, five_years).

        Returns:
            List of OHLC dicts or None if failed.
        """
        # Check cache first
        cache_key = f"{orderbook_id}_{period}"
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]

        self._rate_limit()

        try:
            url = f"{self.BASE_URL}/{orderbook_id}"
            params = {"timePeriod": period}

            response = requests.get(
                url, params=params, headers=self.HEADERS, timeout=10
            )

            if response.status_code != 200:
                return None

            data = response.json()
            ohlc = data.get("ohlc", [])

            if ohlc:
                self._price_cache[cache_key] = ohlc

            return ohlc

        except Exception:
            return None

    def _parse_ohlc(self, ohlc_item: dict, orderbook_id: str) -> PriceSnapshot:
        """Parse OHLC data into PriceSnapshot.

        Args:
            ohlc_item: Dict with timestamp, open, high, low, close, totalVolumeTraded.
            orderbook_id: The orderbookId for symbol reference.

        Returns:
            PriceSnapshot object.
        """
        # Timestamp is in milliseconds
        timestamp = datetime.fromtimestamp(ohlc_item["timestamp"] / 1000)

        return PriceSnapshot(
            symbol=f"AVANZA:{orderbook_id}",
            price=float(ohlc_item["close"]),
            currency="SEK",
            timestamp=timestamp,
            source="avanza",
            open_price=float(ohlc_item.get("open", 0)) or None,
            high_price=float(ohlc_item.get("high", 0)) or None,
            low_price=float(ohlc_item.get("low", 0)) or None,
            volume=int(ohlc_item.get("totalVolumeTraded", 0)) or None,
        )

    def lookup_orderbook_id(self, stock_name: str) -> str | None:
        """Look up orderbookId from stock name.

        Args:
            stock_name: Name of the stock (e.g., "Kopparbergs", "Zinzino").

        Returns:
            orderbookId string or None if not found.
        """
        # Direct lookup
        if stock_name in self.mapping:
            return self.mapping[stock_name]

        # Case-insensitive lookup
        for name, orderbook_id in self.mapping.items():
            if name.lower() == stock_name.lower():
                return orderbook_id

        return None

    def get_current_price(self, symbol: str) -> PriceSnapshot | None:
        """Get current price for an orderbookId.

        Args:
            symbol: The orderbookId (e.g., "13477") or stock name.

        Returns:
            PriceSnapshot with current price or None if unavailable.
        """
        # If symbol is not numeric, try to look it up
        if not symbol.isdigit():
            orderbook_id = self.lookup_orderbook_id(symbol)
            if orderbook_id is None:
                return None
        else:
            orderbook_id = symbol

        # Fetch one_week to get recent data
        ohlc = self._fetch_price_data(orderbook_id, "one_week")

        if not ohlc:
            return None

        # Get the most recent data point
        latest = ohlc[-1]
        return self._parse_ohlc(latest, orderbook_id)

    def get_historical_price(
        self, symbol: str, date: datetime
    ) -> PriceSnapshot | None:
        """Get closing price for a specific historical date.

        Args:
            symbol: The orderbookId (e.g., "13477") or stock name.
            date: The target date.

        Returns:
            PriceSnapshot with closing price or None.
        """
        # If symbol is not numeric, try to look it up
        if not symbol.isdigit():
            orderbook_id = self.lookup_orderbook_id(symbol)
            if orderbook_id is None:
                return None
        else:
            orderbook_id = symbol

        # Determine which period to fetch based on how far back we need
        days_ago = (datetime.now() - date).days
        if days_ago <= 7:
            period = "one_week"
        elif days_ago <= 30:
            period = "one_month"
        elif days_ago <= 90:
            period = "three_months"
        elif days_ago <= 365:
            period = "one_year"
        elif days_ago <= 1095:
            period = "three_years"
        else:
            period = "five_years"

        ohlc = self._fetch_price_data(orderbook_id, period)

        if not ohlc:
            return None

        # Find the closest trading day on or before target date
        target_date = date.date()
        best_match: dict | None = None
        best_diff: int = 999999

        for item in ohlc:
            item_date = datetime.fromtimestamp(item["timestamp"] / 1000).date()
            if item_date <= target_date:
                diff = (target_date - item_date).days
                if diff < best_diff:
                    best_diff = diff
                    best_match = item

        if best_match is None:
            return None

        return self._parse_ohlc(best_match, orderbook_id)

    def get_price_range(
        self, symbol: str, start: datetime, end: datetime
    ) -> list[PriceSnapshot]:
        """Get daily prices over a date range.

        Args:
            symbol: The orderbookId (e.g., "13477") or stock name.
            start: Start date (inclusive).
            end: End date (inclusive).

        Returns:
            List of PriceSnapshot objects for each trading day.
        """
        # If symbol is not numeric, try to look it up
        if not symbol.isdigit():
            orderbook_id = self.lookup_orderbook_id(symbol)
            if orderbook_id is None:
                return []
        else:
            orderbook_id = symbol

        # Always fetch five_years to ensure we have enough data
        ohlc = self._fetch_price_data(orderbook_id, "five_years")

        if not ohlc:
            return []

        snapshots: list[PriceSnapshot] = []
        start_date = start.date()
        end_date = end.date()

        for item in ohlc:
            item_date = datetime.fromtimestamp(item["timestamp"] / 1000).date()
            if start_date <= item_date <= end_date:
                snapshots.append(self._parse_ohlc(item, orderbook_id))

        return snapshots

    @property
    def source_name(self) -> str:
        """Return source identifier.

        Returns:
            "avanza"
        """
        return "avanza"

    def is_available(self, symbol: str) -> bool:
        """Check if price data is available for a symbol.

        Args:
            symbol: The orderbookId or stock name.

        Returns:
            True if data is available.
        """
        return self.get_current_price(symbol) is not None
