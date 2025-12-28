"""CoinGecko API client for crypto price data.

This module provides integration with CoinGecko's free API for
fetching current and historical cryptocurrency prices.
"""

from __future__ import annotations

import time
from datetime import datetime
from functools import lru_cache
from typing import Any

import requests


class CoinGeckoClient:
    """CoinGecko API client for crypto price data.

    Uses the free tier with rate limiting (10-30 calls/minute).

    Example:
        >>> client = CoinGeckoClient()
        >>> price = client.get_current_price("BTC")
        >>> print(f"Bitcoin: ${price:,.2f}")
    """

    BASE_URL = "https://api.coingecko.com/api/v3"

    # Map common symbols to CoinGecko IDs
    SYMBOL_TO_ID = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "XRP": "ripple",
        "ADA": "cardano",
        "DOGE": "dogecoin",
        "DOT": "polkadot",
        "AVAX": "avalanche-2",
        "LINK": "chainlink",
        "MATIC": "matic-network",
        "UNI": "uniswap",
        "ATOM": "cosmos",
        "LTC": "litecoin",
        "BCH": "bitcoin-cash",
        "XLM": "stellar",
        "ALGO": "algorand",
        "NEAR": "near",
        "FTM": "fantom",
        "AAVE": "aave",
        "MKR": "maker",
        "CRV": "curve-dao-token",
        "APE": "apecoin",
        "SAND": "the-sandbox",
        "MANA": "decentraland",
        "AXS": "axie-infinity",
        "SHIB": "shiba-inu",
        "ARB": "arbitrum",
        "OP": "optimism",
        "SUI": "sui",
        "SEI": "sei-network",
        "TIA": "celestia",
    }

    def __init__(
        self,
        api_key: str | None = None,
        rate_limit_delay: float = 1.5,
    ) -> None:
        """Initialize the client.

        Args:
            api_key: Optional CoinGecko Pro API key.
            rate_limit_delay: Delay between requests in seconds.
        """
        self.api_key = api_key
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self._last_request_time = 0.0

        if api_key:
            self.session.headers["x-cg-pro-api-key"] = api_key

    def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict:
        """Make GET request with rate limiting.

        Args:
            endpoint: API endpoint path.
            params: Query parameters.

        Returns:
            JSON response data.

        Raises:
            requests.HTTPError: On API errors.
        """
        self._rate_limit()

        url = f"{self.BASE_URL}{endpoint}"
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()

        return response.json()

    def get_coin_id(self, symbol: str) -> str | None:
        """Get CoinGecko ID for a symbol.

        Args:
            symbol: Crypto symbol (BTC, ETH, etc.).

        Returns:
            CoinGecko ID or None if not found.
        """
        return self.SYMBOL_TO_ID.get(symbol.upper())

    def get_current_price(
        self,
        symbol: str,
        currency: str = "usd",
    ) -> float | None:
        """Get current price for a crypto asset.

        Args:
            symbol: Crypto symbol (BTC, ETH, etc.).
            currency: Currency for price (default: usd).

        Returns:
            Current price or None if not found.

        Example:
            >>> price = client.get_current_price("BTC")
            >>> print(f"${price:,.2f}")
        """
        coin_id = self.get_coin_id(symbol)
        if not coin_id:
            return None

        try:
            data = self._get(
                "/simple/price",
                params={"ids": coin_id, "vs_currencies": currency},
            )
            return data.get(coin_id, {}).get(currency)
        except requests.HTTPError:
            return None

    def get_multiple_prices(
        self,
        symbols: list[str],
        currency: str = "usd",
    ) -> dict[str, float]:
        """Get prices for multiple assets.

        Args:
            symbols: List of crypto symbols.
            currency: Currency for prices.

        Returns:
            Dictionary mapping symbol to price.
        """
        # Map symbols to IDs
        coin_ids = []
        symbol_to_id_map = {}
        for symbol in symbols:
            coin_id = self.get_coin_id(symbol)
            if coin_id:
                coin_ids.append(coin_id)
                symbol_to_id_map[coin_id] = symbol.upper()

        if not coin_ids:
            return {}

        try:
            data = self._get(
                "/simple/price",
                params={"ids": ",".join(coin_ids), "vs_currencies": currency},
            )

            # Map back to symbols
            result = {}
            for coin_id, prices in data.items():
                symbol = symbol_to_id_map.get(coin_id)
                if symbol and currency in prices:
                    result[symbol] = prices[currency]

            return result

        except requests.HTTPError:
            return {}

    def get_historical_price(
        self,
        symbol: str,
        date: datetime,
        currency: str = "usd",
    ) -> float | None:
        """Get price at a specific historical date.

        Args:
            symbol: Crypto symbol.
            date: Date to get price for.
            currency: Currency for price.

        Returns:
            Price at that date or None.

        Example:
            >>> price = client.get_historical_price("BTC", datetime(2024, 1, 1))
        """
        coin_id = self.get_coin_id(symbol)
        if not coin_id:
            return None

        date_str = date.strftime("%d-%m-%Y")

        try:
            data = self._get(
                f"/coins/{coin_id}/history",
                params={"date": date_str, "localization": "false"},
            )
            return data.get("market_data", {}).get("current_price", {}).get(currency)
        except requests.HTTPError:
            return None

    def get_price_range(
        self,
        symbol: str,
        days: int = 30,
        currency: str = "usd",
    ) -> list[tuple[datetime, float]]:
        """Get daily prices for a date range.

        Args:
            symbol: Crypto symbol.
            days: Number of days to look back.
            currency: Currency for prices.

        Returns:
            List of (datetime, price) tuples.

        Example:
            >>> prices = client.get_price_range("BTC", days=7)
            >>> for dt, price in prices:
            ...     print(f"{dt.date()}: ${price:,.2f}")
        """
        coin_id = self.get_coin_id(symbol)
        if not coin_id:
            return []

        try:
            data = self._get(
                f"/coins/{coin_id}/market_chart",
                params={"vs_currency": currency, "days": days},
            )

            prices = []
            for timestamp_ms, price in data.get("prices", []):
                dt = datetime.fromtimestamp(timestamp_ms / 1000)
                prices.append((dt, price))

            return prices

        except requests.HTTPError:
            return []

    def get_price_at_time(
        self,
        symbol: str,
        timestamp: datetime,
        currency: str = "usd",
    ) -> float | None:
        """Get approximate price at a specific time.

        Uses range data and interpolates to find closest price.

        Args:
            symbol: Crypto symbol.
            timestamp: Target timestamp.
            currency: Currency for price.

        Returns:
            Approximate price or None.
        """
        # Get data around the target date
        days_ago = (datetime.now() - timestamp).days + 1
        if days_ago < 1:
            return self.get_current_price(symbol, currency)
        if days_ago > 365:
            # Use historical endpoint for old dates
            return self.get_historical_price(symbol, timestamp, currency)

        prices = self.get_price_range(symbol, days=min(days_ago + 7, 365), currency=currency)
        if not prices:
            return None

        # Find closest price
        target_ts = timestamp.timestamp()
        closest = min(prices, key=lambda x: abs(x[0].timestamp() - target_ts))

        return closest[1]

    def get_coin_info(self, symbol: str) -> dict | None:
        """Get detailed info for a coin.

        Args:
            symbol: Crypto symbol.

        Returns:
            Coin info dictionary or None.
        """
        coin_id = self.get_coin_id(symbol)
        if not coin_id:
            return None

        try:
            return self._get(
                f"/coins/{coin_id}",
                params={
                    "localization": "false",
                    "tickers": "false",
                    "community_data": "false",
                    "developer_data": "false",
                },
            )
        except requests.HTTPError:
            return None

    @lru_cache(maxsize=100)
    def get_market_cap(self, symbol: str, currency: str = "usd") -> float | None:
        """Get current market cap for a coin.

        Args:
            symbol: Crypto symbol.
            currency: Currency for market cap.

        Returns:
            Market cap or None.
        """
        info = self.get_coin_info(symbol)
        if not info:
            return None

        return info.get("market_data", {}).get("market_cap", {}).get(currency)

    def search_coins(self, query: str) -> list[dict]:
        """Search for coins by name or symbol.

        Args:
            query: Search query.

        Returns:
            List of matching coins.
        """
        try:
            data = self._get("/search", params={"query": query})
            return data.get("coins", [])[:10]
        except requests.HTTPError:
            return []

    def add_symbol_mapping(self, symbol: str, coin_id: str) -> None:
        """Add a custom symbol to coin ID mapping.

        Args:
            symbol: Symbol to add.
            coin_id: CoinGecko coin ID.
        """
        self.SYMBOL_TO_ID[symbol.upper()] = coin_id
