"""MFN.se historical press release scraper.

Scrapes historical press releases from MFN.se for backtesting.
Respects rate limits and stores data locally.

Example usage::

    from podstock.news_trader.backtest.mfn_scraper import MFNScraper

    scraper = MFNScraper()
    releases = scraper.scrape_company("cheffelo", days_back=90)
    scraper.save_to_json("data/mfn_releases.json")
"""

from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

import requests


@dataclass
class PressRelease:
    """A press release from MFN."""
    guid: str
    company_slug: str
    title: str
    description: str
    link: str
    pub_datetime: datetime
    language: str
    scope: str  # Country code
    is_regulatory: bool
    tags: list[str]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        d['pub_datetime'] = self.pub_datetime.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'PressRelease':
        """Create from dictionary."""
        d['pub_datetime'] = datetime.fromisoformat(d['pub_datetime'])
        return cls(**d)


class MFNScraper:
    """Scraper for MFN.se press releases.

    Attributes:
        rate_limit_delay: Seconds between requests
        releases: List of scraped press releases
    """

    BASE_URL = "https://mfn.se"
    NS = {'x': 'https://mfn.se/schemas/rss-ns-x/'}

    # Known Swedish company slugs on MFN
    # This can be expanded or auto-discovered
    SWEDISH_COMPANIES = [
        # Large cap
        'investor', 'volvo', 'ericsson', 'atlas-copco', 'abb',
        'sandvik', 'seb', 'handelsbanken', 'nordea', 'swedbank',
        'hm', 'assa-abloy', 'hexagon', 'alfa-laval', 'skf',
        'electrolux', 'essity', 'telia', 'epiroc', 'nibe',
        'evolution', 'spotify', 'klarna',
        # Mid cap examples
        'cheffelo', 'sinch', 'embracer', 'stillfront',
        'paradox-interactive', 'thule', 'addlife', 'addtech',
        'beijer-ref', 'bufab', 'bravida', 'coor', 'dometic',
        'fagerhult', 'hexpol', 'indutrade', 'intrum',
        'iss', 'kinnevik', 'latour', 'lifco', 'loomis',
        'medicover', 'millicom', 'munters', 'ncc', 'peab',
        'saab', 'securitas', 'skanska', 'ssab', 'sweco',
        'swedish-match', 'trelleborg', 'vitrolife', 'wihlborgs',
        # Small cap / First North examples
        'aak', 'bioarctic', 'boozt', 'catena', 'clas-ohlson',
        'collector', 'duni', 'enea', 'fingerprint', 'fortnox',
        'garo', 'hansa-biopharma', 'hemnet', 'imcd', 'karo-pharma',
        'kindred', 'lime', 'lime-technologies', 'mips', 'netent',
        'new-wave', 'nobia', 'nordic-waterproofing', 'oem-international',
        'orexo', 'platzer', 'proact', 'qliro', 'resurs',
        'sagax', 'scandi-standard', 'sdiptech', 'sectra', 'setred',
        'smart-eye', 'storytel', 'surgical-science', 'systemair',
        'tobii', 'vimian', 'vitec', 'xano', 'xvivo',
    ]

    def __init__(self, rate_limit_delay: float = 1.0):
        """Initialize scraper.

        Args:
            rate_limit_delay: Seconds between requests to be nice to MFN
        """
        self.rate_limit_delay = rate_limit_delay
        self.releases: list[PressRelease] = []
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'PodStock-Backtester/1.0 (research purposes)',
        })
        self._last_request_time = 0.0

    def _rate_limit(self):
        """Apply rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def scrape_company_rss(self, company_slug: str) -> list[PressRelease]:
        """Scrape press releases for a company via RSS.

        Args:
            company_slug: Company identifier on MFN (e.g., "cheffelo")

        Returns:
            List of PressRelease objects
        """
        self._rate_limit()

        url = f"{self.BASE_URL}/all/a/{company_slug}.rss"

        try:
            response = self._session.get(url, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching {company_slug}: {e}")
            return []

        releases = []

        try:
            root = ET.fromstring(response.content)

            for item in root.findall('.//item'):
                release = self._parse_rss_item(item, company_slug)
                if release:
                    releases.append(release)

        except ET.ParseError as e:
            print(f"Error parsing RSS for {company_slug}: {e}")
            return []

        return releases

    def _parse_rss_item(self, item: ET.Element, company_slug: str) -> Optional[PressRelease]:
        """Parse an RSS item element."""
        guid = item.findtext('guid', '')
        title = item.findtext('title', '')
        description = item.findtext('description', '')
        link = item.findtext('link', '')
        pub_date = item.findtext('pubDate', '')

        # MFN extensions
        language = item.findtext('x:language', namespaces=self.NS) or 'unknown'
        scope = item.findtext('x:scope', namespaces=self.NS) or 'unknown'
        tags = [t.text for t in item.findall('x:tag', namespaces=self.NS) if t.text]

        is_regulatory = any(':regulatory' in t for t in tags)

        # Parse datetime
        pub_datetime = None
        if pub_date:
            try:
                pub_datetime = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
            except ValueError:
                return None

        if not pub_datetime or not title:
            return None

        # Generate guid if missing
        if not guid:
            guid = hashlib.md5(f"{title}{pub_date}".encode()).hexdigest()

        return PressRelease(
            guid=guid,
            company_slug=company_slug,
            title=title,
            description=description,
            link=link,
            pub_datetime=pub_datetime,
            language=language,
            scope=scope,
            is_regulatory=is_regulatory,
            tags=tags,
        )

    def scrape_global_rss(self, filter_country: str = "SE") -> list[PressRelease]:
        """Scrape the global MFN RSS feed.

        Args:
            filter_country: Only include releases from this country

        Returns:
            List of PressRelease objects
        """
        self._rate_limit()

        url = f"{self.BASE_URL}/all/s.rss"

        try:
            response = self._session.get(url, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching global feed: {e}")
            return []

        releases = []

        try:
            root = ET.fromstring(response.content)

            for item in root.findall('.//item'):
                # Extract company slug from link
                link = item.findtext('link', '')
                company_slug = self._extract_company_from_link(link)

                release = self._parse_rss_item(item, company_slug)
                if release and release.scope == filter_country:
                    releases.append(release)

        except ET.ParseError as e:
            print(f"Error parsing global RSS: {e}")
            return []

        return releases

    def _extract_company_from_link(self, link: str) -> str:
        """Extract company slug from MFN link."""
        # Link format: https://mfn.se/a/company-slug/press-release-slug
        parts = link.replace(self.BASE_URL, '').split('/')
        for i, part in enumerate(parts):
            if part == 'a' and i + 1 < len(parts):
                return parts[i + 1]
        return 'unknown'

    def scrape_multiple_companies(
        self,
        companies: Optional[list[str]] = None,
        progress_callback: Optional[callable] = None,
    ) -> list[PressRelease]:
        """Scrape multiple companies.

        Args:
            companies: List of company slugs (defaults to SWEDISH_COMPANIES)
            progress_callback: Function(company, index, total) for progress updates

        Returns:
            All scraped press releases
        """
        companies = companies or self.SWEDISH_COMPANIES
        all_releases = []

        for i, company in enumerate(companies):
            if progress_callback:
                progress_callback(company, i + 1, len(companies))

            releases = self.scrape_company_rss(company)
            all_releases.extend(releases)

            # Print progress
            print(f"[{i+1}/{len(companies)}] {company}: {len(releases)} releases")

        self.releases = all_releases
        return all_releases

    def filter_by_date(
        self,
        releases: Optional[list[PressRelease]] = None,
        days_back: int = 90,
    ) -> list[PressRelease]:
        """Filter releases by date.

        Args:
            releases: Releases to filter (defaults to self.releases)
            days_back: Only include releases from last N days

        Returns:
            Filtered releases
        """
        releases = releases or self.releases
        cutoff = datetime.now(tz=releases[0].pub_datetime.tzinfo if releases else None) - timedelta(days=days_back)

        return [r for r in releases if r.pub_datetime >= cutoff]

    def filter_regulatory_only(
        self,
        releases: Optional[list[PressRelease]] = None,
    ) -> list[PressRelease]:
        """Filter to only regulatory releases."""
        releases = releases or self.releases
        return [r for r in releases if r.is_regulatory]

    def filter_swedish_only(
        self,
        releases: Optional[list[PressRelease]] = None,
        language: str = "sv",
    ) -> list[PressRelease]:
        """Filter to only Swedish language releases."""
        releases = releases or self.releases
        return [r for r in releases if r.language == language and r.scope == "SE"]

    def save_to_json(self, filepath: str | Path):
        """Save scraped releases to JSON file.

        Args:
            filepath: Output file path
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'scraped_at': datetime.now().isoformat(),
            'count': len(self.releases),
            'releases': [r.to_dict() for r in self.releases],
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Saved {len(self.releases)} releases to {filepath}")

    def load_from_json(self, filepath: str | Path) -> list[PressRelease]:
        """Load releases from JSON file.

        Args:
            filepath: Input file path

        Returns:
            List of PressRelease objects
        """
        filepath = Path(filepath)

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.releases = [PressRelease.from_dict(r) for r in data['releases']]
        print(f"Loaded {len(self.releases)} releases from {filepath}")
        return self.releases


def main():
    """CLI for MFN scraper."""
    import argparse

    parser = argparse.ArgumentParser(description='MFN Press Release Scraper')
    parser.add_argument('--companies', nargs='+', help='Company slugs to scrape')
    parser.add_argument('--all', action='store_true', help='Scrape all known Swedish companies')
    parser.add_argument('--output', default='data/mfn_releases.json', help='Output file')
    parser.add_argument('--rate-limit', type=float, default=1.0, help='Seconds between requests')

    args = parser.parse_args()

    scraper = MFNScraper(rate_limit_delay=args.rate_limit)

    if args.all:
        scraper.scrape_multiple_companies()
    elif args.companies:
        scraper.scrape_multiple_companies(args.companies)
    else:
        # Default: scrape a few companies for testing
        test_companies = ['cheffelo', 'evolution', 'sinch', 'embracer', 'spotify']
        scraper.scrape_multiple_companies(test_companies)

    scraper.save_to_json(args.output)


if __name__ == '__main__':
    main()
