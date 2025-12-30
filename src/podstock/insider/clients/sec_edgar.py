"""SEC EDGAR client for US insider transactions.

Fetches Form 4 filings from the SEC EDGAR database to get
insider transaction data for US-listed companies.

API docs: https://www.sec.gov/developer
Rate limit: 10 requests/second
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any

import httpx

from podstock.insider.base_client import InsiderClient
from podstock.insider.exceptions import ParseError, RateLimitExceededError, TickerNotFoundError
from podstock.insider.models import (
    InsiderReport,
    InsiderRole,
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
        self._throttle_lock = asyncio.Lock()

    async def _throttle(self) -> None:
        """Enforce rate limiting between requests."""
        async with self._throttle_lock:
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
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.CIK_MAPPING_URL,
                    headers={"User-Agent": USER_AGENT},
                )
                if response.status_code == 429:
                    raise RateLimitExceededError()
                response.raise_for_status()
                self._cik_cache = self._parse_cik_mapping(response.json())
                return self._cik_cache
        except httpx.HTTPError as e:
            raise ParseError("sec_edgar", f"Network error fetching CIK mapping: {e}") from e

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
            TickerNotFoundError: If ticker not in SEC database.
            RateLimitExceededError: If SEC rate limit hit.
            ParseError: If response cannot be parsed.
        """
        ticker_upper = ticker.upper()
        mapping = await self._get_cik_mapping()

        if ticker_upper not in mapping:
            raise TickerNotFoundError(ticker)

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
