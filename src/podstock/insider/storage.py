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
        ├── cache/{source}/{TICKER}.json
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
        cache_dir = self.base_path / "cache" / source
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"{ticker.upper()}.json"

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

    def save_report(self, report: InsiderReport, company_slug: str) -> Path:
        """Save insider report to disk.

        Args:
            report: The report to save.
            company_slug: Slugified company name.

        Returns:
            Path where report was saved.
        """
        path = self.get_report_path(company_slug, report.ticker)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load_report(self, path: Path) -> InsiderReport:
        """Load insider report from disk.

        Args:
            path: Path to report file.

        Returns:
            Loaded InsiderReport.
        """
        from podstock.insider.models import InsiderReport

        data = json.loads(path.read_text(encoding="utf-8"))
        return InsiderReport.model_validate(data)

    def save_cache(self, report: InsiderReport, source: str) -> Path:
        """Save report to cache.

        Args:
            report: The report to cache.
            source: Data source identifier.

        Returns:
            Path where cache was saved.
        """
        path = self.get_cache_path(report.ticker, source)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load_cache(self, ticker: str, source: str) -> InsiderReport | None:
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
        data = json.loads(path.read_text(encoding="utf-8"))
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
