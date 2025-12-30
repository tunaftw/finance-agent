"""Tests for podstock.insider module."""

from __future__ import annotations

from datetime import date, datetime

from podstock.insider.exceptions import (
    InsiderError,
    ParseError,
    RateLimitExceededError,
    SourceUnavailableError,
    TickerNotFoundError,
)
from podstock.insider.models import (
    InsiderReport,
    InsiderRole,
    InsiderTransaction,
    TransactionType,
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


class TestInsiderRole:
    """Tests for InsiderRole enum."""

    def test_all_roles_exist(self) -> None:
        """Should have all expected roles."""
        assert InsiderRole.CEO == "ceo"
        assert InsiderRole.CFO == "cfo"
        assert InsiderRole.DIRECTOR == "director"
        assert InsiderRole.OFFICER == "officer"
        assert InsiderRole.MAJOR_SHAREHOLDER == "major_shareholder"
        assert InsiderRole.OTHER == "other"


class TestTransactionType:
    """Tests for TransactionType enum."""

    def test_all_types_exist(self) -> None:
        """Should have all expected transaction types."""
        assert TransactionType.BUY == "buy"
        assert TransactionType.SELL == "sell"
        assert TransactionType.GIFT == "gift"
        assert TransactionType.EXERCISE == "exercise"
        assert TransactionType.OTHER == "other"


class TestInsiderTransaction:
    """Tests for InsiderTransaction model."""

    def test_create_transaction_basic(self) -> None:
        """Should create transaction with required fields."""
        tx = InsiderTransaction(
            insider_name="Tim Cook",
            role=InsiderRole.CEO,
            transaction_type=TransactionType.SELL,
            shares=50000,
            total_value=12500000.0,
            currency="USD",
            transaction_date=date(2025, 12, 15),
            filing_date=date(2025, 12, 16),
            source="sec_edgar",
        )
        assert tx.insider_name == "Tim Cook"
        assert tx.role == InsiderRole.CEO
        assert tx.shares == 50000

    def test_create_transaction_with_optional_fields(self) -> None:
        """Should create transaction with all fields."""
        tx = InsiderTransaction(
            insider_name="Tim Cook",
            role=InsiderRole.CEO,
            transaction_type=TransactionType.SELL,
            shares=50000,
            price=250.0,
            total_value=12500000.0,
            currency="USD",
            transaction_date=date(2025, 12, 15),
            filing_date=date(2025, 12, 16),
            shares_after=500000,
            source="sec_edgar",
            source_url="https://sec.gov/filing/123",
        )
        assert tx.price == 250.0
        assert tx.shares_after == 500000
        assert tx.source_url == "https://sec.gov/filing/123"


class TestInsiderReport:
    """Tests for InsiderReport model."""

    def test_create_report_empty(self) -> None:
        """Should create report with no transactions."""
        report = InsiderReport(
            ticker="AAPL",
            company_name="Apple Inc.",
            market="US",
            transactions=[],
            period_days=90,
            fetched_at=datetime.now(),
        )
        assert report.ticker == "AAPL"
        assert len(report.transactions) == 0

    def test_create_report_with_transactions(self) -> None:
        """Should create report with transactions."""
        tx = InsiderTransaction(
            insider_name="Tim Cook",
            role=InsiderRole.CEO,
            transaction_type=TransactionType.SELL,
            shares=50000,
            total_value=12500000.0,
            currency="USD",
            transaction_date=date(2025, 12, 15),
            filing_date=date(2025, 12, 16),
            source="sec_edgar",
        )
        report = InsiderReport(
            ticker="AAPL",
            company_name="Apple Inc.",
            market="US",
            transactions=[tx],
            period_days=90,
            fetched_at=datetime.now(),
        )
        assert len(report.transactions) == 1
        assert report.transactions[0].insider_name == "Tim Cook"
