"""Ticker mapping for resolving company names to stock symbols.

This module provides functionality for mapping company names mentioned
in podcasts/tweets to their proper ticker symbols.

The TickerMapper maintains a JSON file with:
- Direct mappings: "Evolution" -> "EVO.ST"
- Aliases: "evo" -> "Evolution" (then resolved to ticker)
- Crypto symbols: List of known crypto tickers (BTC-USD, ETH-USD, etc.)

Features:
- Fuzzy matching for approximate name lookups
- Automatic saving when mappings are added
- Support for both stock and crypto tickers

Example usage::

    from pathlib import Path
    from podstock.prices import TickerMapper

    mapper = TickerMapper(Path("data/prices/ticker_mapping.json"))

    # Direct lookup
    ticker = mapper.lookup("Evolution")  # Returns "EVO.ST"

    # Fuzzy search
    results = mapper.search("evol", limit=5)  # Returns similar matches

    # Add new mapping
    mapper.add_mapping("Paradox Interactive", "PDX.ST")

    # Check if crypto
    is_crypto = mapper.is_crypto("BTC-USD")  # Returns True
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz, process

from podstock.prices.exceptions import TickerNotFoundError


class TickerMapper:
    """Resolve company names to ticker symbols.

    Uses a JSON file for persistent storage of mappings and
    supports fuzzy matching for approximate lookups.

    Attributes:
        mapping_file: Path to the JSON mapping file.

    Methods
    -------
    lookup(name)
        Look up ticker by company name. Returns None if not found.
    lookup_strict(name)
        Look up ticker, raises TickerNotFoundError if not found.
    search(query, limit)
        Fuzzy search for company names.
    add_mapping(name, ticker)
        Add a new company name to ticker mapping.
    add_alias(alias, name)
        Add an alias for a company name.
    is_crypto(ticker)
        Check if a ticker is a crypto symbol.
    get_all_mappings()
        Get all name to ticker mappings.
    get_stats()
        Get statistics about the mapping database.

    Example:
        >>> mapper = TickerMapper(Path("data/prices/ticker_mapping.json"))
        >>> ticker = mapper.lookup("Evolution")
        >>> print(ticker)  # EVO.ST
    """

    def __init__(self, mapping_file: Path):
        """Initialize the mapper.

        Args:
            mapping_file: Path to the JSON mapping file.
        """
        self.mapping_file = mapping_file
        self._mappings: dict[str, str] = {}
        self._aliases: dict[str, str] = {}
        self._crypto_symbols: set[str] = set()
        self._load()

    def _load(self) -> None:
        """Load mappings from JSON file."""
        if not self.mapping_file.exists():
            self._mappings = {}
            self._aliases = {}
            self._crypto_symbols = set()
            return

        try:
            data = json.loads(self.mapping_file.read_text(encoding="utf-8"))
            self._mappings = data.get("mappings", {})
            self._aliases = data.get("aliases", {})
            self._crypto_symbols = set(data.get("crypto_symbols", []))
        except (json.JSONDecodeError, OSError):
            self._mappings = {}
            self._aliases = {}
            self._crypto_symbols = set()

    def _save(self) -> None:
        """Save mappings to JSON file (atomic write)."""
        self.mapping_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": 1,
            "updated_at": datetime.now().isoformat(),
            "mappings": self._mappings,
            "aliases": self._aliases,
            "crypto_symbols": sorted(self._crypto_symbols),
        }

        # Atomic write via temp file
        tmp_file = self.mapping_file.with_suffix(".tmp")
        tmp_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp_file.replace(self.mapping_file)

    def lookup(
        self,
        name: str,
        fuzzy_threshold: int = 80,
    ) -> str | None:
        """Resolve company name to ticker.

        Strategy:
        1. Exact match in mappings
        2. Case-insensitive exact match
        3. Alias lookup
        4. Fuzzy match if above threshold

        Args:
            name: Company name to look up.
            fuzzy_threshold: Minimum fuzzy match score (0-100).
                Set to 0 to disable fuzzy matching.

        Returns:
            Ticker symbol or None if not found.

        Example:
            >>> mapper.lookup("Evolution")
            'EVO.ST'
            >>> mapper.lookup("evo")  # case-insensitive
            'EVO.ST'
            >>> mapper.lookup("Evoltion")  # fuzzy match
            'EVO.ST'
        """
        # Exact match
        if name in self._mappings:
            return self._mappings[name]

        # Case-insensitive match
        name_lower = name.lower()
        for key, ticker in self._mappings.items():
            if key.lower() == name_lower:
                return ticker

        # Alias lookup
        if name_lower in self._aliases:
            canonical = self._aliases[name_lower]
            return self._mappings.get(canonical)

        # Fuzzy match
        if fuzzy_threshold > 0 and self._mappings:
            names = list(self._mappings.keys())
            match = process.extractOne(name, names, scorer=fuzz.ratio)

            if match and match[1] >= fuzzy_threshold:
                return self._mappings[match[0]]

        return None

    def lookup_strict(self, name: str) -> str:
        """Resolve company name to ticker (raises if not found).

        Args:
            name: Company name to look up.

        Returns:
            Ticker symbol.

        Raises:
            TickerNotFoundError: If name cannot be resolved.
        """
        ticker = self.lookup(name)
        if ticker is None:
            raise TickerNotFoundError(name)
        return ticker

    def add_mapping(self, name: str, ticker: str) -> None:
        """Add a new company name to ticker mapping.

        Args:
            name: Company name.
            ticker: Ticker symbol.

        Example:
            >>> mapper.add_mapping("Evolution", "EVO.ST")
        """
        self._mappings[name] = ticker
        self._save()

    def add_alias(self, alias: str, canonical_name: str) -> None:
        """Add an alias for an existing company name.

        Args:
            alias: Alternative name.
            canonical_name: The canonical name that has a mapping.

        Example:
            >>> mapper.add_alias("evo", "Evolution")
        """
        self._aliases[alias.lower()] = canonical_name
        self._save()

    def add_crypto(self, symbol: str) -> None:
        """Mark a symbol as a crypto asset.

        Args:
            symbol: Crypto symbol (BTC, ETH, etc.).
        """
        self._crypto_symbols.add(symbol.upper())
        self._save()

    def is_crypto(self, symbol: str) -> bool:
        """Check if a symbol is a known crypto asset.

        Args:
            symbol: Symbol to check.

        Returns:
            True if it's a crypto asset.
        """
        return symbol.upper() in self._crypto_symbols

    def remove_mapping(self, name: str) -> bool:
        """Remove a mapping.

        Args:
            name: Company name to remove.

        Returns:
            True if mapping was removed.
        """
        if name in self._mappings:
            del self._mappings[name]
            self._save()
            return True
        return False

    def list_all(self) -> dict[str, str]:
        """Return all mappings.

        Returns:
            Dictionary of name -> ticker mappings.
        """
        return self._mappings.copy()

    def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[tuple[str, str, int]]:
        """Search mappings by fuzzy matching.

        Args:
            query: Search query.
            limit: Maximum number of results.

        Returns:
            List of (name, ticker, score) tuples.
        """
        if not self._mappings:
            return []

        results = process.extract(
            query,
            list(self._mappings.keys()),
            scorer=fuzz.ratio,
            limit=limit,
        )

        return [(name, self._mappings[name], int(score)) for name, score, _ in results]

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the mapping table.

        Returns:
            Dictionary with stats.
        """
        markets: dict[str, int] = {}
        for ticker in self._mappings.values():
            if ".ST" in ticker:
                market = "Sweden"
            elif ".HE" in ticker:
                market = "Finland"
            elif ".CO" in ticker:
                market = "Denmark"
            elif ".OL" in ticker:
                market = "Norway"
            elif "." in ticker:
                market = "Other"
            else:
                market = "US"

            markets[market] = markets.get(market, 0) + 1

        return {
            "total_mappings": len(self._mappings),
            "total_aliases": len(self._aliases),
            "crypto_symbols": len(self._crypto_symbols),
            "by_market": markets,
        }
