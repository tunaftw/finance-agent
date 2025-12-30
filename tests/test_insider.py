"""Tests for podstock.insider module."""

from __future__ import annotations

from podstock.insider.exceptions import (
    InsiderError,
    ParseError,
    RateLimitExceededError,
    SourceUnavailableError,
    TickerNotFoundError,
)


class TestInsiderExceptions:
    """Tests for insider exception classes."""

    def test_insider_error_is_base_exception(self) -> None:
        """InsiderError should be the base exception."""
        error = InsiderError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_source_unavailable_error(self) -> None:
        """SourceUnavailableError should include market code."""
        error = SourceUnavailableError("NO")
        assert error.market == "NO"
        assert "NO" in str(error)

    def test_ticker_not_found_error(self) -> None:
        """TickerNotFoundError should include ticker."""
        error = TickerNotFoundError("INVALID.XX")
        assert error.ticker == "INVALID.XX"
        assert "INVALID.XX" in str(error)

    def test_rate_limit_exceeded_error(self) -> None:
        """RateLimitExceededError should include retry_after."""
        error = RateLimitExceededError(retry_after=60)
        assert error.retry_after == 60
        assert "60" in str(error)

    def test_rate_limit_exceeded_error_without_retry_after(self) -> None:
        """RateLimitExceededError should work without retry_after."""
        error = RateLimitExceededError()
        assert error.retry_after is None
        assert "retry after" not in str(error)

    def test_parse_error(self) -> None:
        """ParseError should include source."""
        error = ParseError("sec_edgar", "Invalid XML")
        assert error.source == "sec_edgar"
        assert "Invalid XML" in str(error)
