"""Tests for podstock.insider module."""

from __future__ import annotations

import pytest

from podstock.insider.exceptions import (
    InsiderError,
    SourceUnavailable,
    TickerNotFound,
    RateLimitExceeded,
    ParseError,
)


class TestInsiderExceptions:
    """Tests for insider exception classes."""

    def test_insider_error_is_base_exception(self) -> None:
        """InsiderError should be the base exception."""
        error = InsiderError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_source_unavailable(self) -> None:
        """SourceUnavailable should include market code."""
        error = SourceUnavailable("NO")
        assert error.market == "NO"
        assert "NO" in str(error)

    def test_ticker_not_found(self) -> None:
        """TickerNotFound should include ticker."""
        error = TickerNotFound("INVALID.XX")
        assert error.ticker == "INVALID.XX"
        assert "INVALID.XX" in str(error)

    def test_rate_limit_exceeded(self) -> None:
        """RateLimitExceeded should include retry_after."""
        error = RateLimitExceeded(retry_after=60)
        assert error.retry_after == 60
        assert "60" in str(error)

    def test_parse_error(self) -> None:
        """ParseError should include source."""
        error = ParseError("sec_edgar", "Invalid XML")
        assert error.source == "sec_edgar"
        assert "Invalid XML" in str(error)
