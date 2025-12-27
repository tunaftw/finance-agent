"""Company matching for news items.

This module handles matching news items to tracked companies
based on ticker symbols, company names, and ISIN codes.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from podstock.news.models import CompanyMatch, NewsItem

if TYPE_CHECKING:
    from podstock.filings.models import Company
    from podstock.filings.storage import FilingsStorage


class CompanyMatcher:
    """Match news items to tracked companies.

    Uses ticker symbols, company names, and ISIN codes to identify
    which companies are mentioned in news headlines and summaries.

    Example:
        >>> matcher = CompanyMatcher(filings_storage)
        >>> matches = matcher.match_news_item(news_item)
        >>> for m in matches:
        ...     print(f"{m.ticker}: {m.match_confidence}")
    """

    def __init__(self, filings_storage: FilingsStorage):
        """Initialize matcher with filings storage.

        Args:
            filings_storage: FilingsStorage instance for accessing tracked companies.
        """
        self.filings_storage = filings_storage
        self._build_lookup_tables()

    def _build_lookup_tables(self) -> None:
        """Build lookup tables from tracked companies."""
        companies = self.filings_storage.list_companies()

        self.ticker_map: dict[str, Company] = {}
        self.name_map: dict[str, Company] = {}
        self.followed_ids: set[str] = set()

        for company in companies:
            self.followed_ids.add(company.id)

            if company.ticker:
                # Handle multi-class shares: "VOLVO B" -> ["VOLVO", "VOLVO B"]
                ticker_upper = company.ticker.upper()
                self.ticker_map[ticker_upper] = company

                # Also map base ticker without share class
                base_ticker = ticker_upper.split()[0]
                if base_ticker != ticker_upper:
                    self.ticker_map[base_ticker] = company

            # Normalized name for matching
            norm_name = self._normalize_name(company.name)
            self.name_map[norm_name] = company

    def _normalize_name(self, name: str) -> str:
        """Normalize company name for matching.

        Removes common suffixes like AB, Inc, Ltd, etc.
        """
        name = name.lower().strip()

        # Remove common suffixes
        suffixes = [
            r"\s+ab$",
            r"\s+inc\.?$",
            r"\s+ltd\.?$",
            r"\s+plc$",
            r"\s+corp\.?$",
            r"\s+asa$",
            r"\s+oyj$",
            r"\s+a/s$",
            r"\s+\(publ\)$",
        ]
        for suffix in suffixes:
            name = re.sub(suffix, "", name, flags=re.IGNORECASE)

        # Remove extra whitespace
        name = " ".join(name.split())

        return name

    def refresh(self) -> None:
        """Refresh lookup tables from storage.

        Call this after adding/removing companies.
        """
        self._build_lookup_tables()

    def match_news_item(self, item: NewsItem) -> list[CompanyMatch]:
        """Extract company references from news item.

        Args:
            item: News item to match.

        Returns:
            List of company matches found in the news item.
        """
        matches: list[CompanyMatch] = []
        seen_ids: set[str] = set()

        # Combine title and summary for matching
        text = f"{item.title} {item.summary or ''}"

        # 1. Check for ticker symbols
        tickers_found = self._extract_tickers(text)
        for ticker in tickers_found:
            if ticker in self.ticker_map:
                company = self.ticker_map[ticker]
                if company.id not in seen_ids:
                    seen_ids.add(company.id)
                    matches.append(CompanyMatch(
                        company_id=company.id,
                        ticker=company.ticker,
                        match_type="ticker",
                        match_confidence=1.0,
                        is_followed=company.id in self.followed_ids,
                    ))

        # 2. Check for company names
        for norm_name, company in self.name_map.items():
            if company.id in seen_ids:
                continue

            # Check if normalized name appears in text
            if self._name_in_text(norm_name, text):
                seen_ids.add(company.id)
                matches.append(CompanyMatch(
                    company_id=company.id,
                    ticker=company.ticker,
                    match_type="name_exact",
                    match_confidence=0.9,
                    is_followed=company.id in self.followed_ids,
                ))

        return matches

    def _extract_tickers(self, text: str) -> list[str]:
        """Extract potential ticker symbols from text.

        Swedish tickers can be like: EVO, VOLVO B, SEB A, ERIC B
        """
        # Pattern for Swedish tickers (2-6 uppercase letters, optionally followed by space and A/B)
        pattern = r'\b([A-Z]{2,6}(?:\s+[AB])?)\b'
        candidates = re.findall(pattern, text)

        # Filter to only known tickers
        return [t for t in candidates if t in self.ticker_map]

    def _name_in_text(self, norm_name: str, text: str) -> bool:
        """Check if normalized company name appears in text."""
        # Case-insensitive word boundary match
        pattern = r'\b' + re.escape(norm_name) + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))


def create_matcher_if_available() -> CompanyMatcher | None:
    """Create a CompanyMatcher if filings storage is available.

    Returns:
        CompanyMatcher instance, or None if filings not configured.
    """
    try:
        from podstock.core.config import load_config
        from podstock.filings.storage import FilingsStorage

        config = load_config()
        filings_storage = FilingsStorage(config)

        # Only create matcher if we have companies
        companies = filings_storage.list_companies()
        if companies:
            return CompanyMatcher(filings_storage)

        return None

    except Exception:
        return None
