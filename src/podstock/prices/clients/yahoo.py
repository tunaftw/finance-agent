"""Yahoo Finance price client using yfinance library.

This module provides the YahooFinanceClient for fetching stock and crypto prices
from Yahoo Finance. It handles:
- Swedish stocks (.ST suffix)
- Nordic stocks (Finland .HE, Denmark .CO, Norway .OL)
- US stocks (no suffix)
- Crypto (via -USD suffix, e.g., BTC-USD, ETH-USD)

Features:
- Rate limiting to avoid being blocked
- Automatic market suffix handling
- Historical and current price fetching
- OHLCV data support

Example usage::

    from podstock.prices.clients.yahoo import YahooFinanceClient

    client = YahooFinanceClient()

    # Get current price
    snapshot = client.get_current_price("EVO.ST")
    print(f"Evolution: {snapshot.price} {snapshot.currency}")

    # Get historical price
    from datetime import datetime
    hist = client.get_historical_price("EVO.ST", datetime(2024, 6, 15))

    # Get crypto price
    btc = client.get_current_price("BTC-USD")
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Literal

import yfinance as yf

from podstock.prices.clients.base import PriceClient
from podstock.prices.exceptions import InvalidTickerError
from podstock.prices.models import PriceSnapshot


class YahooFinanceClient(PriceClient):
    """Yahoo Finance price client with rate limiting and Nordic stock support.

    Handles Swedish stocks by automatically adding .ST suffix when needed.
    Implements rate limiting to avoid being blocked by Yahoo Finance.
    Also supports crypto via -USD suffix (e.g., BTC-USD, ETH-USD).

    Attributes:
        rate_limit_delay: Seconds to wait between requests.
        default_currency: Default currency for prices.

    Class Attributes:
        MARKET_SUFFIX: Mapping of market to ticker suffix.
        MARKET_CURRENCY: Mapping of market to currency code.

    Methods
    -------
    get_current_price(symbol)
        Get current price for a symbol.
    get_historical_price(symbol, date)
        Get closing price for a specific historical date.
    get_price_range(symbol, start, end)
        Get daily prices over a date range.
    normalize_ticker(ticker, market)
        Add exchange suffix if needed.
    get_currency_for_ticker(ticker)
        Determine currency based on ticker suffix.
    is_crypto(ticker)
        Check if ticker is a crypto asset.
    validate_ticker(ticker)
        Validate that a ticker exists and has data.

    Example:
        >>> client = YahooFinanceClient()
        >>> price = client.get_current_price("EVO.ST")
        >>> print(f"Evolution: {price.price} {price.currency}")
    """

    # Market suffix mapping
    MARKET_SUFFIX: dict[str, str] = {
        "sweden": ".ST",
        "us": "",
        "europe": "",
        "finland": ".HE",
        "denmark": ".CO",
        "norway": ".OL",
    }

    # Currency by market
    MARKET_CURRENCY: dict[str, str] = {
        "sweden": "SEK",
        "us": "USD",
        "europe": "EUR",
        "finland": "EUR",
        "denmark": "DKK",
        "norway": "NOK",
    }

    def __init__(
        self,
        rate_limit_delay: float = 0.5,
        default_currency: str = "SEK",
    ):
        """Initialize the Yahoo Finance client.

        Args:
            rate_limit_delay: Seconds to wait between API requests.
            default_currency: Default currency to use.
        """
        self.rate_limit_delay = rate_limit_delay
        self.default_currency = default_currency
        self._last_request_time: float = 0.0

    def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def normalize_ticker(
        self,
        ticker: str,
        market: str = "sweden",
    ) -> str:
        """Add exchange suffix if needed.

        Args:
            ticker: The base ticker symbol.
            market: Market classification (sweden, us, europe, etc.).

        Returns:
            Ticker with appropriate suffix.

        Examples:
            >>> client.normalize_ticker("EVO", "sweden")
            'EVO.ST'
            >>> client.normalize_ticker("AAPL", "us")
            'AAPL'
            >>> client.normalize_ticker("EVO.ST", "sweden")
            'EVO.ST'
        """
        # Already has a suffix
        if "." in ticker:
            return ticker

        suffix = self.MARKET_SUFFIX.get(market.lower(), "")
        return f"{ticker}{suffix}"

    def get_currency_for_ticker(self, ticker: str) -> str:
        """Determine currency based on ticker suffix.

        Args:
            ticker: The ticker symbol.

        Returns:
            Currency code (SEK, USD, etc.).
        """
        # Crypto tickers end with -USD
        if ticker.endswith("-USD"):
            return "USD"
        elif ticker.endswith(".ST"):
            return "SEK"
        elif ticker.endswith(".HE"):
            return "EUR"
        elif ticker.endswith(".CO"):
            return "DKK"
        elif ticker.endswith(".OL"):
            return "NOK"
        elif "." not in ticker and "-" not in ticker:
            return "USD"  # Assume US stock
        return self.default_currency

    def is_crypto(self, ticker: str) -> bool:
        """Check if ticker is a crypto asset.

        Args:
            ticker: The ticker symbol.

        Returns:
            True if ticker is crypto (ends with -USD).
        """
        return ticker.endswith("-USD")

    def get_current_price(self, symbol: str) -> PriceSnapshot | None:
        """Get current price for a symbol.

        Args:
            symbol: The ticker symbol (e.g., "EVO.ST").

        Returns:
            PriceSnapshot with current price or None if unavailable.
        """
        self._rate_limit()

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Try different price fields
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            if price is None:
                # Fallback to last close
                hist = ticker.history(period="1d")
                if hist.empty:
                    return None
                price = float(hist["Close"].iloc[-1])

            currency = info.get("currency", self.get_currency_for_ticker(symbol))

            return PriceSnapshot(
                symbol=symbol,
                price=float(price),
                currency=currency.upper(),
                timestamp=datetime.now(),
                source="yahoo",
                open_price=info.get("open") or info.get("regularMarketOpen"),
                high_price=info.get("dayHigh") or info.get("regularMarketDayHigh"),
                low_price=info.get("dayLow") or info.get("regularMarketDayLow"),
                volume=info.get("volume") or info.get("regularMarketVolume"),
            )

        except Exception:
            return None

    def get_historical_price(
        self, symbol: str, date: datetime
    ) -> PriceSnapshot | None:
        """Get closing price for a specific historical date.

        Handles weekends and holidays by finding the nearest trading day.

        Args:
            symbol: The ticker symbol.
            date: The target date.

        Returns:
            PriceSnapshot with closing price or None.
        """
        self._rate_limit()

        try:
            ticker = yf.Ticker(symbol)

            # Fetch a 5-day window to handle weekends/holidays
            start = date - timedelta(days=5)
            end = date + timedelta(days=1)

            hist = ticker.history(start=start, end=end)

            if hist.empty:
                return None

            # Find closest trading day on or before target date
            target_date = date.date()
            matching_dates = [d.date() for d in hist.index if d.date() <= target_date]

            if not matching_dates:
                return None

            closest_date = max(matching_dates)
            row = hist.loc[hist.index.date == closest_date].iloc[0]

            currency = self.get_currency_for_ticker(symbol)

            return PriceSnapshot(
                symbol=symbol,
                price=float(row["Close"]),
                currency=currency,
                timestamp=datetime.combine(closest_date, datetime.min.time()),
                source="yahoo",
                open_price=float(row["Open"]) if "Open" in row else None,
                high_price=float(row["High"]) if "High" in row else None,
                low_price=float(row["Low"]) if "Low" in row else None,
                volume=int(row["Volume"]) if "Volume" in row else None,
            )

        except Exception:
            return None

    def get_price_range(
        self, symbol: str, start: datetime, end: datetime
    ) -> list[PriceSnapshot]:
        """Get daily prices over a date range.

        Args:
            symbol: The ticker symbol.
            start: Start date (inclusive).
            end: End date (inclusive).

        Returns:
            List of PriceSnapshot objects for each trading day.
        """
        self._rate_limit()

        snapshots: list[PriceSnapshot] = []

        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start, end=end + timedelta(days=1))

            if hist.empty:
                return snapshots

            currency = self.get_currency_for_ticker(symbol)

            for idx, row in hist.iterrows():
                snapshots.append(
                    PriceSnapshot(
                        symbol=symbol,
                        price=float(row["Close"]),
                        currency=currency,
                        timestamp=idx.to_pydatetime(),  # type: ignore
                        source="yahoo",
                        open_price=float(row["Open"]) if "Open" in row else None,
                        high_price=float(row["High"]) if "High" in row else None,
                        low_price=float(row["Low"]) if "Low" in row else None,
                        volume=int(row["Volume"]) if "Volume" in row else None,
                    )
                )

            return snapshots

        except Exception:
            return snapshots

    @property
    def source_name(self) -> str:
        """Return source identifier.

        Returns:
            "yahoo"
        """
        return "yahoo"

    def validate_ticker(self, ticker: str) -> bool:
        """Validate that a ticker exists and has data.

        Args:
            ticker: The ticker symbol to validate.

        Returns:
            True if ticker is valid and has price data.
        """
        return self.get_current_price(ticker) is not None
