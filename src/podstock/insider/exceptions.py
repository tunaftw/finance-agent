"""Custom exceptions for insider module.

This module defines exceptions that may occur during
fetching or parsing of insider transaction data.
"""

from __future__ import annotations


class InsiderError(Exception):
    """Base exception for insider module errors."""

    pass


class SourceUnavailable(InsiderError):
    """Market/source not yet supported."""

    def __init__(self, market: str) -> None:
        self.market = market
        super().__init__(f"Insider data source not available for market: {market}")


class TickerNotFound(InsiderError):
    """Could not map ticker to company in source."""

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(f"Ticker not found in insider registry: {ticker}")


class RateLimitExceeded(InsiderError):
    """Hit API rate limit, retry later."""

    def __init__(self, retry_after: int | None = None) -> None:
        self.retry_after = retry_after
        msg = "Rate limit exceeded"
        if retry_after:
            msg += f", retry after {retry_after} seconds"
        super().__init__(msg)


class ParseError(InsiderError):
    """Failed to parse response from source."""

    def __init__(self, source: str, message: str) -> None:
        self.source = source
        super().__init__(f"Failed to parse {source} response: {message}")
