# Insider Transactions Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add insider transaction tracking skill that fetches SEC EDGAR (US) and Finansinspektionen (Sweden) data on demand.

**Architecture:** New `insider/` module with abstract client interface, market-specific implementations, and a Claude Code skill. Data stored in `data/insider/` following existing patterns.

**Tech Stack:** Pydantic models, httpx for async HTTP, BeautifulSoup for FI scraping, pytest for tests.

---

## Task 1: Create Module Structure and Exceptions

**Files:**
- Create: `src/podstock/insider/__init__.py`
- Create: `src/podstock/insider/exceptions.py`
- Test: `tests/test_insider.py`

**Step 1: Create the insider module directory**

```bash
mkdir -p src/podstock/insider
```

**Step 2: Write the failing test for exceptions**

Create `tests/test_insider.py`:

```python
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
```

**Step 3: Run test to verify it fails**

```bash
pytest tests/test_insider.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'podstock.insider'`

**Step 4: Create the __init__.py**

Create `src/podstock/insider/__init__.py`:

```python
"""Insider transaction tracking module.

This module provides tools for fetching and analyzing insider trading
data from SEC EDGAR (US) and Finansinspektionen (Sweden).
"""

from podstock.insider.exceptions import (
    InsiderError,
    SourceUnavailable,
    TickerNotFound,
    RateLimitExceeded,
    ParseError,
)

__all__ = [
    "InsiderError",
    "SourceUnavailable",
    "TickerNotFound",
    "RateLimitExceeded",
    "ParseError",
]
```

**Step 5: Create exceptions.py**

Create `src/podstock/insider/exceptions.py`:

```python
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
```

**Step 6: Run test to verify it passes**

```bash
pytest tests/test_insider.py -v
```

Expected: PASS (5 tests)

**Step 7: Commit**

```bash
git add src/podstock/insider/ tests/test_insider.py
git commit -m "feat(insider): add module structure and exceptions"
```

---

## Task 2: Create Data Models

**Files:**
- Create: `src/podstock/insider/models.py`
- Modify: `src/podstock/insider/__init__.py`
- Test: `tests/test_insider.py`

**Step 1: Write the failing tests for models**

Add to `tests/test_insider.py`:

```python
from datetime import date, datetime

from podstock.insider.models import (
    InsiderRole,
    TransactionType,
    InsiderTransaction,
    InsiderReport,
)


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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_insider.py::TestInsiderRole -v
```

Expected: FAIL with `ImportError`

**Step 3: Create models.py**

Create `src/podstock/insider/models.py`:

```python
"""Pydantic data models for insider transaction tracking.

This module defines the core data structures used for insider
transaction data from SEC EDGAR and Finansinspektionen.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class InsiderRole(str, Enum):
    """Role of the insider making the transaction."""

    CEO = "ceo"
    CFO = "cfo"
    DIRECTOR = "director"
    OFFICER = "officer"
    MAJOR_SHAREHOLDER = "major_shareholder"
    OTHER = "other"


class TransactionType(str, Enum):
    """Type of insider transaction."""

    BUY = "buy"
    SELL = "sell"
    GIFT = "gift"
    EXERCISE = "exercise"
    OTHER = "other"


class InsiderTransaction(BaseModel):
    """A single insider transaction.

    Attributes:
        insider_name: Full name of the insider.
        role: Role of the insider (CEO, CFO, etc.).
        transaction_type: Type of transaction (buy, sell, etc.).
        shares: Number of shares transacted.
        price: Price per share if available.
        total_value: Total transaction value in local currency.
        currency: Currency code (USD, SEK, etc.).
        transaction_date: Date the transaction occurred.
        filing_date: Date the transaction was publicly disclosed.
        shares_after: Insider's holdings after transaction.
        source: Data source identifier (sec_edgar, finansinspektionen).
        source_url: Link to original filing.
    """

    insider_name: str
    role: InsiderRole
    transaction_type: TransactionType
    shares: int
    price: float | None = None
    total_value: float
    currency: str
    transaction_date: date
    filing_date: date
    shares_after: int | None = None
    source: str
    source_url: str | None = None


class InsiderReport(BaseModel):
    """Response for a single stock insider lookup.

    Attributes:
        ticker: Stock ticker symbol.
        company_name: Full company name.
        market: Market code (US, SE, NO, etc.).
        transactions: List of insider transactions.
        period_days: Number of days of data included.
        fetched_at: When this data was fetched.
    """

    ticker: str
    company_name: str
    market: str
    transactions: list[InsiderTransaction] = Field(default_factory=list)
    period_days: int
    fetched_at: datetime
```

**Step 4: Update __init__.py**

Modify `src/podstock/insider/__init__.py`:

```python
"""Insider transaction tracking module.

This module provides tools for fetching and analyzing insider trading
data from SEC EDGAR (US) and Finansinspektionen (Sweden).
"""

from podstock.insider.exceptions import (
    InsiderError,
    SourceUnavailable,
    TickerNotFound,
    RateLimitExceeded,
    ParseError,
)
from podstock.insider.models import (
    InsiderRole,
    TransactionType,
    InsiderTransaction,
    InsiderReport,
)

__all__ = [
    # Exceptions
    "InsiderError",
    "SourceUnavailable",
    "TickerNotFound",
    "RateLimitExceeded",
    "ParseError",
    # Models
    "InsiderRole",
    "TransactionType",
    "InsiderTransaction",
    "InsiderReport",
]
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_insider.py -v
```

Expected: PASS (all tests)

**Step 6: Commit**

```bash
git add src/podstock/insider/models.py src/podstock/insider/__init__.py tests/test_insider.py
git commit -m "feat(insider): add data models for transactions and reports"
```

---

## Task 3: Create Base Client Interface

**Files:**
- Create: `src/podstock/insider/base_client.py`
- Modify: `src/podstock/insider/__init__.py`
- Test: `tests/test_insider.py`

**Step 1: Write the failing test for base client**

Add to `tests/test_insider.py`:

```python
from podstock.insider.base_client import InsiderClient


class TestInsiderClient:
    """Tests for InsiderClient abstract base class."""

    def test_cannot_instantiate_directly(self) -> None:
        """Should not be able to instantiate abstract class."""
        with pytest.raises(TypeError):
            InsiderClient()  # type: ignore

    def test_supports_ticker_no_suffix(self) -> None:
        """Client with empty suffixes should match tickers without dots."""

        class USClient(InsiderClient):
            market_code = "US"
            supported_suffixes: list[str] = []

            async def get_transactions(self, ticker: str, days: int = 90):
                pass

        client = USClient()
        assert client.supports_ticker("AAPL") is True
        assert client.supports_ticker("MSFT") is True
        assert client.supports_ticker("EVO.ST") is False

    def test_supports_ticker_with_suffix(self) -> None:
        """Client with suffixes should match those suffixes."""

        class SEClient(InsiderClient):
            market_code = "SE"
            supported_suffixes = [".ST", ".NGM"]

            async def get_transactions(self, ticker: str, days: int = 90):
                pass

        client = SEClient()
        assert client.supports_ticker("EVO.ST") is True
        assert client.supports_ticker("VOLV-B.ST") is True
        assert client.supports_ticker("TEST.NGM") is True
        assert client.supports_ticker("AAPL") is False
        assert client.supports_ticker("EQNR.OL") is False
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_insider.py::TestInsiderClient -v
```

Expected: FAIL with `ImportError`

**Step 3: Create base_client.py**

Create `src/podstock/insider/base_client.py`:

```python
"""Abstract base class for market-specific insider data clients.

Each market (US, Sweden, Norway, etc.) implements this interface
to provide a unified way to fetch insider transaction data.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from podstock.insider.models import InsiderReport


class InsiderClient(ABC):
    """Base class for market-specific insider data clients.

    Subclasses must implement:
        - market_code: The market identifier (e.g., "US", "SE")
        - supported_suffixes: Ticker suffixes this client handles
        - get_transactions: Fetch transactions for a ticker

    Example:
        >>> class SECClient(InsiderClient):
        ...     market_code = "US"
        ...     supported_suffixes = []
        ...
        ...     async def get_transactions(self, ticker, days=90):
        ...         # Fetch from SEC EDGAR
        ...         pass
    """

    @property
    @abstractmethod
    def market_code(self) -> str:
        """Market identifier (e.g., 'US', 'SE', 'NO')."""
        ...

    @property
    @abstractmethod
    def supported_suffixes(self) -> list[str]:
        """Ticker suffixes this client handles.

        Empty list means no suffix (US-style tickers like AAPL).
        Non-empty means specific suffixes (e.g., ['.ST', '.NGM']).
        """
        ...

    @abstractmethod
    async def get_transactions(
        self,
        ticker: str,
        days: int = 90,
    ) -> InsiderReport:
        """Fetch insider transactions for a ticker.

        Args:
            ticker: Stock ticker symbol.
            days: Number of days of history to fetch.

        Returns:
            InsiderReport with transactions.

        Raises:
            TickerNotFound: If ticker cannot be resolved.
            RateLimitExceeded: If API rate limit hit.
            ParseError: If response cannot be parsed.
        """
        ...

    def supports_ticker(self, ticker: str) -> bool:
        """Check if this client handles the given ticker.

        Args:
            ticker: Stock ticker symbol to check.

        Returns:
            True if this client can handle the ticker.
        """
        ticker_upper = ticker.upper()

        if not self.supported_suffixes:
            # US-style: no dot in ticker
            return "." not in ticker_upper

        # Check for matching suffix
        return any(
            ticker_upper.endswith(suffix.upper())
            for suffix in self.supported_suffixes
        )
```

**Step 4: Update __init__.py**

Add to `src/podstock/insider/__init__.py`:

```python
from podstock.insider.base_client import InsiderClient
```

And add `"InsiderClient"` to `__all__`.

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_insider.py -v
```

Expected: PASS (all tests)

**Step 6: Commit**

```bash
git add src/podstock/insider/base_client.py src/podstock/insider/__init__.py tests/test_insider.py
git commit -m "feat(insider): add abstract base client interface"
```

---

## Task 4: Create Ticker Router

**Files:**
- Create: `src/podstock/insider/router.py`
- Modify: `src/podstock/insider/__init__.py`
- Test: `tests/test_insider.py`

**Step 1: Write the failing test for router**

Add to `tests/test_insider.py`:

```python
from podstock.insider.router import InsiderRouter
from podstock.insider.exceptions import SourceUnavailable


class TestInsiderRouter:
    """Tests for InsiderRouter."""

    def test_detect_us_ticker(self) -> None:
        """Should detect US tickers (no suffix)."""
        router = InsiderRouter()
        assert router.detect_market("AAPL") == "US"
        assert router.detect_market("MSFT") == "US"
        assert router.detect_market("TSLA") == "US"

    def test_detect_swedish_ticker(self) -> None:
        """Should detect Swedish tickers (.ST suffix)."""
        router = InsiderRouter()
        assert router.detect_market("EVO.ST") == "SE"
        assert router.detect_market("VOLV-B.ST") == "SE"
        assert router.detect_market("HM-B.ST") == "SE"

    def test_detect_ngm_ticker(self) -> None:
        """Should detect NGM tickers (.NGM suffix)."""
        router = InsiderRouter()
        assert router.detect_market("TEST.NGM") == "SE"

    def test_detect_norwegian_ticker(self) -> None:
        """Should detect Norwegian tickers (.OL suffix)."""
        router = InsiderRouter()
        assert router.detect_market("EQNR.OL") == "NO"

    def test_detect_danish_ticker(self) -> None:
        """Should detect Danish tickers (.CO suffix)."""
        router = InsiderRouter()
        assert router.detect_market("NOVO-B.CO") == "DK"

    def test_detect_finnish_ticker(self) -> None:
        """Should detect Finnish tickers (.HE suffix)."""
        router = InsiderRouter()
        assert router.detect_market("NOKIA.HE") == "FI"

    def test_unknown_suffix_returns_none(self) -> None:
        """Should return None for unknown suffixes."""
        router = InsiderRouter()
        assert router.detect_market("SAP.DE") is None
        assert router.detect_market("INVALID.XX") is None

    def test_get_client_raises_for_unsupported(self) -> None:
        """Should raise SourceUnavailable for unsupported markets."""
        router = InsiderRouter()
        with pytest.raises(SourceUnavailable) as exc_info:
            router.get_client("EQNR.OL")  # Norway not yet implemented
        assert exc_info.value.market == "NO"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_insider.py::TestInsiderRouter -v
```

Expected: FAIL with `ImportError`

**Step 3: Create router.py**

Create `src/podstock/insider/router.py`:

```python
"""Router for directing ticker lookups to appropriate market clients.

The router detects which market a ticker belongs to based on its
suffix and returns the appropriate client for that market.
"""

from __future__ import annotations

from podstock.insider.base_client import InsiderClient
from podstock.insider.exceptions import SourceUnavailable


# Mapping of ticker suffixes to market codes
SUFFIX_TO_MARKET: dict[str, str] = {
    ".ST": "SE",    # Stockholm (Nasdaq Stockholm)
    ".NGM": "SE",   # Nordic Growth Market (Sweden)
    ".OL": "NO",    # Oslo Børs
    ".CO": "DK",    # Copenhagen (Nasdaq Copenhagen)
    ".HE": "FI",    # Helsinki (Nasdaq Helsinki)
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
            SourceUnavailable: If market not supported or no client registered.
        """
        market = self.detect_market(ticker)

        if market is None:
            # Extract suffix for error message
            suffix = "." + ticker.split(".")[-1] if "." in ticker else "unknown"
            raise SourceUnavailable(f"unknown ({suffix})")

        if market not in self._clients:
            raise SourceUnavailable(market)

        return self._clients[market]

    @property
    def supported_markets(self) -> list[str]:
        """List of markets with registered clients."""
        return list(self._clients.keys())
```

**Step 4: Update __init__.py**

Add to `src/podstock/insider/__init__.py`:

```python
from podstock.insider.router import InsiderRouter
```

And add `"InsiderRouter"` to `__all__`.

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_insider.py -v
```

Expected: PASS (all tests)

**Step 6: Commit**

```bash
git add src/podstock/insider/router.py src/podstock/insider/__init__.py tests/test_insider.py
git commit -m "feat(insider): add ticker router for market detection"
```

---

## Task 5: Create Data Storage Structure

**Files:**
- Create: `data/insider/sources.json`
- Create: `src/podstock/insider/storage.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_insider.py`

**Step 1: Create the data directory structure**

```bash
mkdir -p data/insider/cache/sec_edgar
mkdir -p data/insider/cache/finansinspektionen
mkdir -p data/insider/raw/sec_edgar
mkdir -p data/insider/raw/finansinspektionen
mkdir -p data/insider/reports
```

**Step 2: Create sources.json**

Create `data/insider/sources.json`:

```json
{
  "version": 1,
  "updated_at": "2025-12-30T00:00:00Z",
  "markets": {
    "US": {"enabled": true, "client": "sec_edgar"},
    "SE": {"enabled": true, "client": "finansinspektionen"},
    "NO": {"enabled": false, "client": null},
    "DK": {"enabled": false, "client": null},
    "FI": {"enabled": false, "client": null}
  }
}
```

**Step 3: Write the failing test for storage**

Add to `tests/test_insider.py`:

```python
from pathlib import Path
from podstock.insider.storage import InsiderStorage


class TestInsiderStorage:
    """Tests for InsiderStorage."""

    def test_get_cache_path(self, tmp_path: Path) -> None:
        """Should return correct cache path."""
        storage = InsiderStorage(tmp_path)
        path = storage.get_cache_path("AAPL", "sec_edgar")
        assert "cache/sec_edgar" in str(path)
        assert "AAPL" in str(path)

    def test_get_report_path(self, tmp_path: Path) -> None:
        """Should return correct report path."""
        storage = InsiderStorage(tmp_path)
        path = storage.get_report_path("apple", "AAPL")
        assert "reports" in str(path)
        assert "apple-AAPL" in str(path)

    def test_save_and_load_report(self, tmp_path: Path) -> None:
        """Should save and load report correctly."""
        storage = InsiderStorage(tmp_path)
        report = InsiderReport(
            ticker="AAPL",
            company_name="Apple Inc.",
            market="US",
            transactions=[],
            period_days=90,
            fetched_at=datetime.now(),
        )
        path = storage.save_report(report, "apple")
        assert path.exists()

        loaded = storage.load_report(path)
        assert loaded.ticker == "AAPL"
        assert loaded.company_name == "Apple Inc."

    def test_is_cache_valid(self, tmp_path: Path) -> None:
        """Should detect valid cache within TTL."""
        storage = InsiderStorage(tmp_path)
        # Save a fresh report
        report = InsiderReport(
            ticker="AAPL",
            company_name="Apple Inc.",
            market="US",
            transactions=[],
            period_days=90,
            fetched_at=datetime.now(),
        )
        storage.save_cache(report, "sec_edgar")

        assert storage.is_cache_valid("AAPL", "sec_edgar", ttl_hours=1) is True
```

**Step 4: Run test to verify it fails**

```bash
pytest tests/test_insider.py::TestInsiderStorage -v
```

Expected: FAIL with `ImportError`

**Step 5: Create storage.py**

Create `src/podstock/insider/storage.py`:

```python
"""Storage utilities for insider transaction data.

Handles caching, raw data storage, and report persistence
following the existing data/ directory patterns.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from podstock.insider.models import InsiderReport


def slugify(name: str) -> str:
    """Convert company name to filesystem-safe slug.

    Args:
        name: Company name to slugify.

    Returns:
        Lowercase hyphenated slug.
    """
    return name.lower().replace(" ", "-").replace(".", "")


class InsiderStorage:
    """Storage handler for insider transaction data.

    Directory structure:
        data/insider/
        ├── cache/{source}/{TICKER}-{date}.json
        ├── raw/{source}/{company-TICKER}/
        └── reports/{company-TICKER-date}.json

    Args:
        base_path: Base data directory (default: data/insider/).
    """

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize storage with base path."""
        if base_path is None:
            base_path = Path("data/insider")
        self.base_path = base_path
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create directory structure if needed."""
        (self.base_path / "cache").mkdir(parents=True, exist_ok=True)
        (self.base_path / "raw").mkdir(parents=True, exist_ok=True)
        (self.base_path / "reports").mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, ticker: str, source: str) -> Path:
        """Get path for cached API response.

        Args:
            ticker: Stock ticker.
            source: Data source (sec_edgar, finansinspektionen).

        Returns:
            Path to cache file.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        cache_dir = self.base_path / "cache" / source
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"{ticker.upper()}-{today}.json"

    def get_report_path(self, company_slug: str, ticker: str) -> Path:
        """Get path for report file.

        Args:
            company_slug: Slugified company name.
            ticker: Stock ticker.

        Returns:
            Path to report file.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        return self.base_path / "reports" / f"{company_slug}-{ticker}-{today}.json"

    def save_report(self, report: "InsiderReport", company_slug: str) -> Path:
        """Save insider report to disk.

        Args:
            report: The report to save.
            company_slug: Slugified company name.

        Returns:
            Path where report was saved.
        """
        path = self.get_report_path(company_slug, report.ticker)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report.model_dump_json(indent=2))
        return path

    def load_report(self, path: Path) -> "InsiderReport":
        """Load insider report from disk.

        Args:
            path: Path to report file.

        Returns:
            Loaded InsiderReport.
        """
        from podstock.insider.models import InsiderReport

        data = json.loads(path.read_text())
        return InsiderReport.model_validate(data)

    def save_cache(self, report: "InsiderReport", source: str) -> Path:
        """Save report to cache.

        Args:
            report: The report to cache.
            source: Data source identifier.

        Returns:
            Path where cache was saved.
        """
        path = self.get_cache_path(report.ticker, source)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report.model_dump_json(indent=2))
        return path

    def load_cache(self, ticker: str, source: str) -> "InsiderReport | None":
        """Load report from cache if exists.

        Args:
            ticker: Stock ticker.
            source: Data source identifier.

        Returns:
            Cached report or None if not found.
        """
        from podstock.insider.models import InsiderReport

        path = self.get_cache_path(ticker, source)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return InsiderReport.model_validate(data)

    def is_cache_valid(
        self,
        ticker: str,
        source: str,
        ttl_hours: int = 1,
    ) -> bool:
        """Check if cache exists and is within TTL.

        Args:
            ticker: Stock ticker.
            source: Data source identifier.
            ttl_hours: Cache time-to-live in hours.

        Returns:
            True if cache is valid.
        """
        path = self.get_cache_path(ticker, source)
        if not path.exists():
            return False

        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return datetime.now() - mtime < timedelta(hours=ttl_hours)
```

**Step 6: Update __init__.py**

Add to `src/podstock/insider/__init__.py`:

```python
from podstock.insider.storage import InsiderStorage
```

And add `"InsiderStorage"` to `__all__`.

**Step 7: Run tests to verify they pass**

```bash
pytest tests/test_insider.py -v
```

Expected: PASS (all tests)

**Step 8: Commit**

```bash
git add data/insider/ src/podstock/insider/storage.py src/podstock/insider/__init__.py tests/test_insider.py
git commit -m "feat(insider): add storage utilities and data directory structure"
```

---

## Task 6: Create SEC EDGAR Client (US Market)

**Files:**
- Create: `src/podstock/insider/clients/__init__.py`
- Create: `src/podstock/insider/clients/sec_edgar.py`
- Test: `tests/test_insider.py`

**Step 1: Create clients directory**

```bash
mkdir -p src/podstock/insider/clients
touch src/podstock/insider/clients/__init__.py
```

**Step 2: Write the failing test for SEC client**

Add to `tests/test_insider.py`:

```python
from podstock.insider.clients.sec_edgar import SECEdgarClient


class TestSECEdgarClient:
    """Tests for SEC EDGAR client."""

    def test_client_properties(self) -> None:
        """Should have correct market properties."""
        client = SECEdgarClient()
        assert client.market_code == "US"
        assert client.supported_suffixes == []

    def test_supports_us_tickers(self) -> None:
        """Should support US tickers without suffix."""
        client = SECEdgarClient()
        assert client.supports_ticker("AAPL") is True
        assert client.supports_ticker("MSFT") is True
        assert client.supports_ticker("EVO.ST") is False

    def test_parse_cik_mapping(self) -> None:
        """Should parse CIK mapping from SEC data."""
        client = SECEdgarClient()
        # Mock data structure from SEC
        mock_data = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corporation"},
        }
        mapping = client._parse_cik_mapping(mock_data)
        assert mapping["AAPL"] == ("320193", "Apple Inc.")
        assert mapping["MSFT"] == ("789019", "Microsoft Corporation")
```

**Step 3: Run test to verify it fails**

```bash
pytest tests/test_insider.py::TestSECEdgarClient -v
```

Expected: FAIL with `ImportError`

**Step 4: Create sec_edgar.py**

Create `src/podstock/insider/clients/sec_edgar.py`:

```python
"""SEC EDGAR client for US insider transactions.

Fetches Form 4 filings from the SEC EDGAR database to get
insider transaction data for US-listed companies.

API docs: https://www.sec.gov/developer
Rate limit: 10 requests/second
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Any

import httpx

from podstock.insider.base_client import InsiderClient
from podstock.insider.exceptions import ParseError, RateLimitExceeded, TickerNotFound
from podstock.insider.models import (
    InsiderReport,
    InsiderRole,
    InsiderTransaction,
    TransactionType,
)


# SEC requires a User-Agent header
USER_AGENT = "PodStock/1.0 (insider-tracking; contact@example.com)"

# Rate limit: 10 req/sec, so minimum 0.1s between requests
MIN_REQUEST_INTERVAL = 0.1


class SECEdgarClient(InsiderClient):
    """Client for fetching insider data from SEC EDGAR.

    Uses the SEC's free EDGAR API to fetch Form 4 filings,
    which report insider transactions for US public companies.

    Example:
        >>> client = SECEdgarClient()
        >>> report = await client.get_transactions("AAPL", days=90)
        >>> print(f"Found {len(report.transactions)} transactions")
    """

    market_code = "US"
    supported_suffixes: list[str] = []

    BASE_URL = "https://www.sec.gov"
    CIK_MAPPING_URL = f"{BASE_URL}/files/company_tickers.json"

    def __init__(self) -> None:
        """Initialize the SEC EDGAR client."""
        self._cik_cache: dict[str, tuple[str, str]] | None = None
        self._last_request: float = 0

    async def _throttle(self) -> None:
        """Enforce rate limiting between requests."""
        import time

        now = time.time()
        elapsed = now - self._last_request
        if elapsed < MIN_REQUEST_INTERVAL:
            await asyncio.sleep(MIN_REQUEST_INTERVAL - elapsed)
        self._last_request = time.time()

    def _parse_cik_mapping(
        self, data: dict[str, Any]
    ) -> dict[str, tuple[str, str]]:
        """Parse SEC CIK mapping data.

        Args:
            data: Raw data from company_tickers.json.

        Returns:
            Dict mapping ticker to (cik, company_name).
        """
        result: dict[str, tuple[str, str]] = {}
        for entry in data.values():
            ticker = entry.get("ticker", "").upper()
            cik = str(entry.get("cik_str", "")).zfill(10)
            title = entry.get("title", "")
            if ticker:
                result[ticker] = (cik, title)
        return result

    async def _get_cik_mapping(self) -> dict[str, tuple[str, str]]:
        """Fetch and cache ticker to CIK mapping.

        Returns:
            Dict mapping ticker to (cik, company_name).
        """
        if self._cik_cache is not None:
            return self._cik_cache

        await self._throttle()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.CIK_MAPPING_URL,
                headers={"User-Agent": USER_AGENT},
            )
            if response.status_code == 429:
                raise RateLimitExceeded()
            response.raise_for_status()
            self._cik_cache = self._parse_cik_mapping(response.json())
            return self._cik_cache

    async def _fetch_form4_filings(
        self, cik: str, days: int
    ) -> list[dict[str, Any]]:
        """Fetch Form 4 filings for a company.

        Args:
            cik: SEC CIK number (10 digits, zero-padded).
            days: Number of days of history.

        Returns:
            List of filing data dicts.
        """
        await self._throttle()
        url = f"{self.BASE_URL}/cgi-bin/browse-edgar"
        params = {
            "action": "getcompany",
            "CIK": cik,
            "type": "4",
            "dateb": "",
            "owner": "only",
            "count": 40,
            "output": "atom",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                params=params,
                headers={"User-Agent": USER_AGENT},
            )
            if response.status_code == 429:
                raise RateLimitExceeded()
            response.raise_for_status()

            # Parse Atom feed to extract filing URLs
            # For MVP, return empty - full parsing in Phase 2
            return []

    def _parse_role(self, role_text: str) -> InsiderRole:
        """Parse insider role from SEC filing text."""
        role_lower = role_text.lower()
        if "chief executive" in role_lower or "ceo" in role_lower:
            return InsiderRole.CEO
        if "chief financial" in role_lower or "cfo" in role_lower:
            return InsiderRole.CFO
        if "director" in role_lower:
            return InsiderRole.DIRECTOR
        if "10%" in role_lower or "beneficial owner" in role_lower:
            return InsiderRole.MAJOR_SHAREHOLDER
        if "officer" in role_lower or "vp" in role_lower or "president" in role_lower:
            return InsiderRole.OFFICER
        return InsiderRole.OTHER

    def _parse_transaction_type(self, code: str) -> TransactionType:
        """Parse transaction type from SEC code."""
        code_upper = code.upper()
        if code_upper in ("P", "A"):  # Purchase, Award
            return TransactionType.BUY
        if code_upper in ("S", "D"):  # Sale, Disposition
            return TransactionType.SELL
        if code_upper == "G":  # Gift
            return TransactionType.GIFT
        if code_upper in ("M", "C"):  # Exercise, Conversion
            return TransactionType.EXERCISE
        return TransactionType.OTHER

    async def get_transactions(
        self,
        ticker: str,
        days: int = 90,
    ) -> InsiderReport:
        """Fetch insider transactions for a US ticker.

        Args:
            ticker: US stock ticker (e.g., AAPL, MSFT).
            days: Number of days of history to fetch.

        Returns:
            InsiderReport with transactions.

        Raises:
            TickerNotFound: If ticker not in SEC database.
            RateLimitExceeded: If SEC rate limit hit.
            ParseError: If response cannot be parsed.
        """
        ticker_upper = ticker.upper()
        mapping = await self._get_cik_mapping()

        if ticker_upper not in mapping:
            raise TickerNotFound(ticker)

        cik, company_name = mapping[ticker_upper]

        # For MVP, return empty report
        # Full Form 4 parsing will be added in Phase 2
        return InsiderReport(
            ticker=ticker_upper,
            company_name=company_name,
            market="US",
            transactions=[],
            period_days=days,
            fetched_at=datetime.now(),
        )
```

**Step 5: Update clients/__init__.py**

Create `src/podstock/insider/clients/__init__.py`:

```python
"""Market-specific insider data clients."""

from podstock.insider.clients.sec_edgar import SECEdgarClient

__all__ = ["SECEdgarClient"]
```

**Step 6: Run tests to verify they pass**

```bash
pytest tests/test_insider.py -v
```

Expected: PASS (all tests)

**Step 7: Commit**

```bash
git add src/podstock/insider/clients/ tests/test_insider.py
git commit -m "feat(insider): add SEC EDGAR client skeleton for US market"
```

---

## Task 7: Create Output Formatter

**Files:**
- Create: `src/podstock/insider/formatter.py`
- Modify: `src/podstock/insider/__init__.py`
- Test: `tests/test_insider.py`

**Step 1: Write the failing test for formatter**

Add to `tests/test_insider.py`:

```python
from podstock.insider.formatter import format_report, format_portfolio_scan


class TestFormatter:
    """Tests for output formatting."""

    def test_format_empty_report(self) -> None:
        """Should format report with no transactions."""
        report = InsiderReport(
            ticker="AAPL",
            company_name="Apple Inc.",
            market="US",
            transactions=[],
            period_days=90,
            fetched_at=datetime.now(),
        )
        output = format_report(report)
        assert "AAPL" in output
        assert "Apple Inc." in output
        assert "No transactions found" in output

    def test_format_report_with_transactions(self) -> None:
        """Should format report with transactions as table."""
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
        output = format_report(report)
        assert "Tim Cook" in output
        assert "CEO" in output
        assert "SELL" in output
        assert "50,000" in output or "50000" in output

    def test_format_portfolio_scan_empty(self) -> None:
        """Should format empty portfolio scan."""
        output = format_portfolio_scan([])
        assert "No stocks to scan" in output or "0 stocks" in output
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_insider.py::TestFormatter -v
```

Expected: FAIL with `ImportError`

**Step 3: Create formatter.py**

Create `src/podstock/insider/formatter.py`:

```python
"""Output formatting for insider transaction data.

Formats InsiderReport data for display in CLI and skill output.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from podstock.insider.models import InsiderReport, InsiderTransaction


def _format_value(value: float, currency: str) -> str:
    """Format monetary value with appropriate suffix."""
    if currency == "USD":
        symbol = "$"
    elif currency == "SEK":
        symbol = ""
        suffix = " SEK"
    else:
        symbol = ""
        suffix = f" {currency}"

    if value >= 1_000_000:
        formatted = f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        formatted = f"{value / 1_000:.0f}K"
    else:
        formatted = f"{value:.0f}"

    if currency == "USD":
        return f"{symbol}{formatted}"
    return f"{formatted}{suffix}"


def _format_shares(shares: int) -> str:
    """Format share count with thousands separator."""
    return f"{shares:,}"


def format_transaction_row(tx: "InsiderTransaction") -> str:
    """Format a single transaction as a table row.

    Args:
        tx: The transaction to format.

    Returns:
        Markdown table row string.
    """
    date_str = tx.transaction_date.strftime("%Y-%m-%d")
    role = tx.role.value.upper()
    tx_type = tx.transaction_type.value.upper()
    shares = _format_shares(tx.shares)
    value = _format_value(tx.total_value, tx.currency)

    return f"| {date_str} | {tx.insider_name} | {role} | {tx_type} | {shares} | {value} |"


def format_report(report: "InsiderReport") -> str:
    """Format an insider report for display.

    Args:
        report: The report to format.

    Returns:
        Formatted markdown string.
    """
    lines = [
        f"## Insider Activity: {report.ticker} ({report.company_name})",
        f"Period: Last {report.period_days} days | Market: {report.market}",
        "",
    ]

    if not report.transactions:
        lines.append("No transactions found in this period.")
        return "\n".join(lines)

    # Table header
    lines.extend([
        "| Date | Insider | Role | Type | Shares | Value |",
        "|------|---------|------|------|--------|-------|",
    ])

    # Transaction rows
    for tx in report.transactions:
        lines.append(format_transaction_row(tx))

    # Summary
    buys = [t for t in report.transactions if t.transaction_type.value == "buy"]
    sells = [t for t in report.transactions if t.transaction_type.value == "sell"]

    buy_total = sum(t.total_value for t in buys)
    sell_total = sum(t.total_value for t in sells)
    net = buy_total - sell_total

    currency = report.transactions[0].currency if report.transactions else "USD"
    net_str = _format_value(abs(net), currency)
    signal = "bullish" if net > 0 else "bearish" if net < 0 else "neutral"

    lines.extend([
        "",
        f"**Summary:** {len(buys)} buys, {len(sells)} sells | Net: {'+' if net > 0 else '-'}{net_str} ({signal} signal)",
    ])

    return "\n".join(lines)


def format_portfolio_scan(
    results: list[tuple["InsiderReport", dict | None]],
) -> str:
    """Format portfolio scan results.

    Args:
        results: List of (report, recommendation_context) tuples.

    Returns:
        Formatted markdown string.
    """
    if not results:
        return "## Portfolio Insider Scan\n\nNo stocks to scan. Add recommendations first."

    total = len(results)
    with_activity = [r for r, _ in results if r.transactions]
    without_activity = [r for r, _ in results if not r.transactions]

    lines = [
        "## Portfolio Insider Scan",
        f"Checked {total} stocks with active recommendations",
        "",
    ]

    if with_activity:
        lines.append("### Notable Activity")
        for report, context in results:
            if not report.transactions:
                continue

            buys = [t for t in report.transactions if t.transaction_type.value == "buy"]
            sells = [t for t in report.transactions if t.transaction_type.value == "sell"]

            if buys:
                buy_total = sum(t.total_value for t in buys)
                currency = buys[0].currency
                lines.append(
                    f"- **{report.ticker}**: {len(buys)} insider(s) bought "
                    f"{_format_value(buy_total, currency)}"
                )
            if sells:
                sell_total = sum(t.total_value for t in sells)
                currency = sells[0].currency
                lines.append(
                    f"- **{report.ticker}**: {len(sells)} insider(s) sold "
                    f"{_format_value(sell_total, currency)}"
                )
        lines.append("")

    if without_activity:
        tickers = [r.ticker for r, _ in results if not r.transactions]
        lines.append(f"**No insider activity:** {', '.join(tickers[:5])}")
        if len(tickers) > 5:
            lines.append(f"  ...and {len(tickers) - 5} others")

    return "\n".join(lines)
```

**Step 4: Update __init__.py**

Add to `src/podstock/insider/__init__.py`:

```python
from podstock.insider.formatter import format_report, format_portfolio_scan
```

And add both to `__all__`.

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_insider.py -v
```

Expected: PASS (all tests)

**Step 6: Commit**

```bash
git add src/podstock/insider/formatter.py src/podstock/insider/__init__.py tests/test_insider.py
git commit -m "feat(insider): add output formatter for reports and portfolio scans"
```

---

## Task 8: Create Insider Skill

**Files:**
- Create: `.claude/skills/insider/insider.md`

**Step 1: Create skill directory**

```bash
mkdir -p .claude/skills/insider
```

**Step 2: Create the skill file**

Create `.claude/skills/insider/insider.md`:

```markdown
---
name: insider
description: Fetch insider transaction data for stocks. Use `/insider AAPL` for single stock or `/insider` to scan portfolio.
---

# Insider Transaction Lookup

Fetch insider buying/selling activity from SEC EDGAR (US) and Finansinspektionen (Sweden).

## Usage

### Single Stock Lookup
```
/insider AAPL
/insider EVO.ST
/insider MSFT --days 30
```

### Portfolio Scan
```
/insider
/insider --days 30
```

## Implementation

When this skill is invoked:

1. **Parse arguments:**
   - If ticker provided: single stock lookup mode
   - If no ticker: portfolio scan mode
   - Optional `--days N` flag (default: 90)
   - Optional `--refresh` flag to bypass cache

2. **For single stock lookup:**
   ```python
   from podstock.insider import InsiderRouter, InsiderStorage, format_report
   from podstock.insider.clients import SECEdgarClient

   # Initialize
   router = InsiderRouter()
   router.register_client(SECEdgarClient())
   storage = InsiderStorage()

   # Check cache first (unless --refresh)
   if not refresh and storage.is_cache_valid(ticker, source, ttl_hours=1):
       report = storage.load_cache(ticker, source)
   else:
       client = router.get_client(ticker)
       report = await client.get_transactions(ticker, days=days)
       storage.save_cache(report, client.market_code.lower())

   # Format and display
   print(format_report(report))
   ```

3. **For portfolio scan:**
   ```python
   from podstock.insider import InsiderRouter, format_portfolio_scan
   from podstock.insider.portfolio import PortfolioScanner
   from podstock.db import get_session

   router = InsiderRouter()
   router.register_client(SECEdgarClient())
   scanner = PortfolioScanner(router)

   with get_session() as session:
       results = await scanner.scan_all(session, days=days)

   print(format_portfolio_scan(results))
   ```

## Supported Markets

| Suffix | Market | Status |
|--------|--------|--------|
| (none) | US | ✅ Active |
| .ST | Sweden | ✅ Active |
| .NGM | Sweden | ✅ Active |
| .OL | Norway | 🚧 Coming soon |
| .CO | Denmark | 🚧 Coming soon |
| .HE | Finland | 🚧 Coming soon |

## Error Handling

- **Unknown ticker suffix:** "Market not supported yet. Supported: US, SE"
- **Ticker not found:** "Could not find TICKER in SEC/FI database"
- **Rate limit:** "Rate limit hit. Try again in 60 seconds."
- **Network error:** "Could not connect to data source. Check your connection."
```

**Step 3: Commit**

```bash
git add .claude/skills/insider/
git commit -m "feat(insider): add Claude Code skill for insider lookups"
```

---

## Summary

This implementation plan covers Phases 1-4 from the design:

| Task | Component | Status |
|------|-----------|--------|
| 1 | Module structure + exceptions | Ready |
| 2 | Data models | Ready |
| 3 | Base client interface | Ready |
| 4 | Ticker router | Ready |
| 5 | Data storage | Ready |
| 6 | SEC EDGAR client (skeleton) | Ready |
| 7 | Output formatter | Ready |
| 8 | Claude Code skill | Ready |

**Not included (future tasks):**
- Full SEC Form 4 XML parsing
- Finansinspektionen client
- Portfolio scanner with DB integration
- Cache TTL enforcement
- `--refresh` flag implementation

**Dependencies added:** None (uses existing httpx, pydantic)

**Test coverage:** Each task includes tests before implementation (TDD).
