"""MFN RSS feed monitor for real-time press release detection.

Monitors the MFN.se RSS feed for new Nordic press releases and
generates trading signals using the fast rule-based parser.

Example usage::

    from podstock.news_trader.feed_monitor import FeedMonitor

    def handle_signal(signal, item):
        print(f"{signal.action}: {item['title']}")

    monitor = FeedMonitor(callback=handle_signal)
    monitor.run()  # Blocks and monitors continuously
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional
from xml.etree import ElementTree as ET

import requests

from podstock.news_trader.parser import PressReleaseParser, TradingSignal, Action


@dataclass
class FeedItem:
    """Parsed RSS feed item."""
    guid: str
    title: str
    description: str
    link: str
    pub_date: str
    pub_datetime: Optional[datetime]
    language: Optional[str]
    tags: list[str]
    scope: Optional[str]  # Country code (SE, NO, DK, FI)
    is_regulatory: bool
    raw_xml: str


@dataclass
class MonitorStats:
    """Statistics for the feed monitor."""
    items_processed: int = 0
    signals_generated: int = 0
    buy_signals: int = 0
    sell_signals: int = 0
    last_check: Optional[datetime] = None
    avg_process_time_ms: float = 0.0
    errors: int = 0


class FeedMonitor:
    """Real-time MFN RSS feed monitor.

    Polls the MFN feed at configurable intervals and processes
    new press releases through the trading signal parser.

    Attributes:
        feed_url: URL of the MFN RSS feed
        poll_interval: Seconds between feed checks (min 30 per Nasdaq rules)
        parser: Press release parser instance
        callback: Function called for each new signal
        stats: Monitoring statistics
    """

    # MFN RSS feed URLs
    FEEDS = {
        'all': 'https://mfn.se/all/s.rss',  # All Nordic companies
        'sweden': 'https://mfn.se/all/s/sweden.rss',  # Swedish only (if exists)
    }

    # Namespaces used in MFN RSS
    NS = {
        'x': 'https://mfn.se/schemas/rss-ns-x/',
    }

    def __init__(
        self,
        feed_url: str = 'https://mfn.se/all/s.rss',
        poll_interval: float = 30.0,  # Nasdaq minimum
        callback: Optional[Callable[[TradingSignal, FeedItem], None]] = None,
        filter_countries: Optional[list[str]] = None,  # e.g., ['SE']
        filter_regulatory_only: bool = True,
        min_confidence: str = "LOW",  # LOW, MEDIUM, HIGH
    ):
        """Initialize the feed monitor.

        Args:
            feed_url: MFN RSS feed URL to monitor
            poll_interval: Seconds between checks (min 30)
            callback: Function(signal, item) called for new items
            filter_countries: Only process items from these countries
            filter_regulatory_only: Only process regulatory news (MAR)
            min_confidence: Minimum signal confidence to report
        """
        self.feed_url = feed_url
        self.poll_interval = max(30.0, poll_interval)  # Enforce minimum
        self.parser = PressReleaseParser()
        self.callback = callback
        self.filter_countries = filter_countries
        self.filter_regulatory_only = filter_regulatory_only
        self.min_confidence = min_confidence

        self._seen_guids: set[str] = set()
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'PodStock-NewsTrader/1.0',
        })

        self.stats = MonitorStats()

    def fetch_feed(self) -> list[FeedItem]:
        """Fetch and parse the RSS feed.

        Returns:
            List of FeedItem objects from the feed
        """
        response = self._session.get(self.feed_url, timeout=10)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        items = []

        for item in root.findall('.//item'):
            try:
                parsed = self._parse_item(item)
                if parsed:
                    items.append(parsed)
            except Exception as e:
                self.stats.errors += 1
                continue

        return items

    def _parse_item(self, item: ET.Element) -> Optional[FeedItem]:
        """Parse a single RSS item element."""
        guid = item.findtext('guid', '')
        title = item.findtext('title', '')
        description = item.findtext('description', '')
        link = item.findtext('link', '')
        pub_date = item.findtext('pubDate', '')

        # Parse MFN-specific extensions
        language = item.findtext('x:language', namespaces=self.NS)
        scope = item.findtext('x:scope', namespaces=self.NS)

        # Get all tags
        tags = [tag.text for tag in item.findall('x:tag', namespaces=self.NS) if tag.text]

        # Check if regulatory (MAR)
        is_regulatory = any(':regulatory' in tag for tag in tags)

        # Parse datetime
        pub_datetime = None
        if pub_date:
            try:
                # Format: "Mon, 19 Jan 2026 10:30:00 +0000"
                pub_datetime = datetime.strptime(
                    pub_date, "%a, %d %b %Y %H:%M:%S %z"
                )
            except ValueError:
                pass

        # Create hash if no guid
        if not guid:
            guid = hashlib.md5(f"{title}{pub_date}".encode()).hexdigest()

        return FeedItem(
            guid=guid,
            title=title,
            description=description,
            link=link,
            pub_date=pub_date,
            pub_datetime=pub_datetime,
            language=language,
            tags=tags,
            scope=scope,
            is_regulatory=is_regulatory,
            raw_xml=ET.tostring(item, encoding='unicode'),
        )

    def process_item(self, item: FeedItem) -> Optional[TradingSignal]:
        """Process a single feed item and return trading signal.

        Args:
            item: Parsed feed item

        Returns:
            TradingSignal if item passes filters, None otherwise
        """
        # Apply filters
        if self.filter_countries and item.scope not in self.filter_countries:
            return None

        if self.filter_regulatory_only and not item.is_regulatory:
            return None

        # Analyze with parser
        start = time.perf_counter()
        signal = self.parser.analyze(item.title, item.description)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Update stats
        self.stats.items_processed += 1
        self.stats.avg_process_time_ms = (
            (self.stats.avg_process_time_ms * (self.stats.items_processed - 1) + elapsed_ms)
            / self.stats.items_processed
        )

        # Filter by confidence
        confidence_order = ["LOW", "MEDIUM", "HIGH"]
        if confidence_order.index(signal.confidence.value) < confidence_order.index(self.min_confidence):
            return None

        # Update signal stats
        self.stats.signals_generated += 1
        if signal.action in [Action.BUY, Action.STRONG_BUY]:
            self.stats.buy_signals += 1
        elif signal.action in [Action.SELL, Action.STRONG_SELL]:
            self.stats.sell_signals += 1

        return signal

    def check_once(self) -> list[tuple[TradingSignal, FeedItem]]:
        """Check feed once and return new signals.

        Returns:
            List of (signal, item) tuples for new items
        """
        results = []

        try:
            items = self.fetch_feed()
            self.stats.last_check = datetime.now()

            for item in items:
                # Skip already seen
                if item.guid in self._seen_guids:
                    continue

                self._seen_guids.add(item.guid)

                # Process and get signal
                signal = self.process_item(item)
                if signal and signal.action != Action.SKIP:
                    results.append((signal, item))

                    # Call callback if set
                    if self.callback:
                        self.callback(signal, item)

        except Exception as e:
            self.stats.errors += 1
            raise

        return results

    def run(self, max_iterations: Optional[int] = None):
        """Run the monitor continuously.

        Args:
            max_iterations: Stop after N iterations (None = run forever)
        """
        iteration = 0

        # Initial fetch to populate seen set
        print(f"[{datetime.now().isoformat()}] Starting feed monitor...")
        print(f"Feed: {self.feed_url}")
        print(f"Poll interval: {self.poll_interval}s")
        print(f"Filters: countries={self.filter_countries}, regulatory_only={self.filter_regulatory_only}")
        print("-" * 60)

        try:
            initial_items = self.fetch_feed()
            for item in initial_items:
                self._seen_guids.add(item.guid)
            print(f"Initialized with {len(initial_items)} existing items")
            print("-" * 60)
        except Exception as e:
            print(f"Error during initialization: {e}")

        while max_iterations is None or iteration < max_iterations:
            iteration += 1

            try:
                time.sleep(self.poll_interval)
                results = self.check_once()

                for signal, item in results:
                    self._print_signal(signal, item)

            except KeyboardInterrupt:
                print("\nStopping monitor...")
                break
            except Exception as e:
                print(f"[ERROR] {e}")
                continue

        self._print_stats()

    def _print_signal(self, signal: TradingSignal, item: FeedItem):
        """Print a trading signal to console."""
        # Color codes
        colors = {
            Action.STRONG_BUY: '\033[92m',   # Green
            Action.BUY: '\033[92m',
            Action.HOLD: '\033[93m',          # Yellow
            Action.SELL: '\033[91m',          # Red
            Action.STRONG_SELL: '\033[91m',
            Action.SKIP: '\033[90m',          # Gray
        }
        reset = '\033[0m'
        color = colors.get(signal.action, '')

        timestamp = item.pub_datetime.strftime("%H:%M:%S") if item.pub_datetime else "??:??:??"

        print(f"\n{'='*60}")
        print(f"[{timestamp}] {color}{signal.action.value}{reset} ({signal.confidence.value})")
        print(f"Type: {signal.news_type.value}")
        print(f"Title: {item.title[:80]}...")
        print(f"Reason: {signal.reason}")
        if signal.ticker_hint:
            print(f"Ticker: {signal.ticker_hint}")
        print(f"Link: {item.link}")
        print(f"{'='*60}")

    def _print_stats(self):
        """Print monitoring statistics."""
        print("\n" + "=" * 60)
        print("MONITOR STATISTICS")
        print("=" * 60)
        print(f"Items processed: {self.stats.items_processed}")
        print(f"Signals generated: {self.stats.signals_generated}")
        print(f"  - Buy signals: {self.stats.buy_signals}")
        print(f"  - Sell signals: {self.stats.sell_signals}")
        print(f"Avg process time: {self.stats.avg_process_time_ms:.2f} ms")
        print(f"Errors: {self.stats.errors}")
        print("=" * 60)


def main():
    """Run the feed monitor from command line."""
    import argparse

    argparser = argparse.ArgumentParser(description='MFN Feed Monitor')
    argparser.add_argument('--feed', default='https://mfn.se/all/s.rss', help='RSS feed URL')
    argparser.add_argument('--interval', type=float, default=30, help='Poll interval (seconds)')
    argparser.add_argument('--country', default='SE', help='Filter by country (SE, NO, DK, FI)')
    argparser.add_argument('--all-countries', action='store_true', help='Monitor all countries')
    argparser.add_argument('--all-news', action='store_true', help='Include non-regulatory news')
    argparser.add_argument('--min-confidence', default='MEDIUM', choices=['LOW', 'MEDIUM', 'HIGH'])

    args = argparser.parse_args()

    countries = None if args.all_countries else [args.country]

    monitor = FeedMonitor(
        feed_url=args.feed,
        poll_interval=args.interval,
        filter_countries=countries,
        filter_regulatory_only=not args.all_news,
        min_confidence=args.min_confidence,
    )

    monitor.run()


if __name__ == '__main__':
    main()
