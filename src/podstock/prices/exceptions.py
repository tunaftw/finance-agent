"""Custom exceptions for the prices module.

Exceptions
----------
PriceError
    Base exception for all price-related errors.

TickerNotFoundError(PriceError)
    Raised when a ticker symbol cannot be resolved from a company name.
    Includes the company name that failed to resolve.

PriceNotAvailableError(PriceError)
    Raised when price data cannot be fetched from the data source.
    Includes the symbol and optional date that failed.

InvalidTickerError(PriceError)
    Raised when a ticker symbol is invalid or doesn't exist.
    Includes the invalid ticker.

Example::

    from podstock.prices import PriceTracker, TickerNotFoundError

    tracker = PriceTracker(data_dir)
    try:
        rec = tracker.track_recommendation(
            asset_name="Unknown Company",
            ...
        )
    except TickerNotFoundError as e:
        print(f"Could not find ticker for: {e.name}")
"""


class PriceError(Exception):
    """Base exception for price-related errors."""

    pass


class TickerNotFoundError(PriceError):
    """Raised when a ticker symbol cannot be resolved."""

    def __init__(self, name: str, message: str | None = None):
        self.name = name
        super().__init__(
            message or f"No ticker mapping found for '{name}'. "
            f"Add with: podstock prices mapping add '{name}' <TICKER>"
        )


class PriceNotAvailableError(PriceError):
    """Raised when price data cannot be fetched."""

    def __init__(self, symbol: str, date: str | None = None):
        self.symbol = symbol
        self.date = date
        if date:
            super().__init__(f"Could not fetch price for '{symbol}' on {date}")
        else:
            super().__init__(f"Could not fetch current price for '{symbol}'")


class InvalidTickerError(PriceError):
    """Raised when a ticker symbol is invalid."""

    def __init__(self, ticker: str):
        self.ticker = ticker
        super().__init__(f"Invalid ticker symbol: '{ticker}'")
