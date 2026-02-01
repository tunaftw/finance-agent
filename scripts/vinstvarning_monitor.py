#!/usr/bin/env python3
"""
Vinstvarning Monitor - Real-time profit warning detector for Swedish stocks.

Monitors MFN RSS feed for profit warnings (vinstvarningar) and generates
trading signals in real-time.

Usage:
    python scripts/vinstvarning_monitor.py              # Monitor Swedish regulatory news
    python scripts/vinstvarning_monitor.py --test       # Test with recent feed items
    python scripts/vinstvarning_monitor.py --backtest   # Analyze historical items
"""

import sys
import time
import argparse
from datetime import datetime
from xml.etree import ElementTree as ET

import requests

sys.path.insert(0, 'src')

from podstock.news_trader.profit_warning_detector import ProfitWarningDetector, WarningType


# ANSI colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BOLD = '\033[1m'
RESET = '\033[0m'


class VinstvarningMonitor:
    """Specialized monitor for Swedish profit warnings."""

    FEED_URL = 'https://mfn.se/all/s.rss'

    NS = {'x': 'https://mfn.se/schemas/rss-ns-x/'}

    def __init__(self):
        self.detector = ProfitWarningDetector()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Vinstvarning-Monitor/1.0'})
        self._seen_guids = set()

    def fetch_feed(self) -> list[dict]:
        """Fetch and parse RSS feed."""
        response = self.session.get(self.FEED_URL, timeout=10)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        items = []

        for item in root.findall('.//item'):
            guid = item.findtext('guid', '')
            title = item.findtext('title', '')
            description = item.findtext('description', '')
            link = item.findtext('link', '')
            pub_date = item.findtext('pubDate', '')

            # MFN extensions
            scope = item.findtext('x:scope', namespaces=self.NS)
            tags = [t.text for t in item.findall('x:tag', namespaces=self.NS) if t.text]
            is_regulatory = any(':regulatory' in t for t in tags)

            # Parse datetime
            pub_datetime = None
            if pub_date:
                try:
                    pub_datetime = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
                except ValueError:
                    pass

            items.append({
                'guid': guid,
                'title': title,
                'description': description,
                'link': link,
                'pub_date': pub_date,
                'pub_datetime': pub_datetime,
                'scope': scope,
                'is_regulatory': is_regulatory,
            })

        return items

    def analyze_item(self, item: dict) -> dict:
        """Analyze a single item for profit warning."""
        start = time.perf_counter()
        result = self.detector.analyze(item['title'], item['description'])
        elapsed_ms = (time.perf_counter() - start) * 1000

        return {
            'item': item,
            'result': result,
            'analysis_time_ms': elapsed_ms,
        }

    def print_alert(self, analysis: dict):
        """Print a profit warning alert."""
        item = analysis['item']
        result = analysis['result']

        if result.warning_type == WarningType.POSITIVE:
            color = GREEN
            icon = "🚀"
        elif result.warning_type == WarningType.NEGATIVE:
            color = RED
            icon = "⚠️"
        else:
            return  # Don't print non-warnings

        timestamp = item['pub_datetime'].strftime("%Y-%m-%d %H:%M:%S") if item['pub_datetime'] else "Unknown"

        print()
        print(f"{BOLD}{'='*70}{RESET}")
        print(f"{icon} {color}{BOLD}VINSTVARNING DETEKTERAD{RESET}")
        print(f"{'='*70}")
        print()
        print(f"  {BOLD}Tid:{RESET}        {timestamp}")
        print(f"  {BOLD}Typ:{RESET}        {color}{result.warning_type.value}{RESET}")
        print(f"  {BOLD}Action:{RESET}     {color}{result.action}{RESET}")
        print(f"  {BOLD}Confidence:{RESET} {result.confidence:.0%}")
        print()
        print(f"  {BOLD}Titel:{RESET}")
        print(f"    {item['title']}")
        print()
        print(f"  {BOLD}Sammanfattning:{RESET}")
        print(f"    {result.summary}")
        print()

        if result.change_percent is not None:
            print(f"  {BOLD}Nyckeltal:{RESET}")
            print(f"    Förändring: {color}{result.change_percent:+.1f}%{RESET} YoY")
            if result.current_value and result.previous_value:
                print(f"    Nuvarande:  {result.current_value:.1f} MSEK")
                print(f"    Föregående: {result.previous_value:.1f} MSEK")
            print()

        if result.reasoning:
            print(f"  {BOLD}Resonemang:{RESET}")
            for r in result.reasoning:
                print(f"    • {r}")
            print()

        print(f"  {BOLD}Länk:{RESET} {item['link']}")
        print(f"  {BOLD}Analystid:{RESET} {analysis['analysis_time_ms']:.2f} ms")
        print(f"{'='*70}")
        print()

    def test_mode(self):
        """Test mode - analyze recent feed items."""
        print(f"{BOLD}VINSTVARNING MONITOR - TEST MODE{RESET}")
        print("=" * 70)
        print()

        print("Hämtar feed...")
        items = self.fetch_feed()
        print(f"Hämtade {len(items)} items")
        print()

        # Filter Swedish regulatory news
        swedish_items = [i for i in items if i['scope'] == 'SE' and i['is_regulatory']]
        print(f"Svenska regulatoriska nyheter: {len(swedish_items)}")
        print()

        warnings_found = 0
        print("Analyserar alla items...")
        print("-" * 70)

        for item in swedish_items:
            analysis = self.analyze_item(item)
            result = analysis['result']

            if result.is_profit_warning:
                warnings_found += 1
                self.print_alert(analysis)
            else:
                # Print one-liner for non-warnings
                timestamp = item['pub_datetime'].strftime("%H:%M") if item['pub_datetime'] else "??:??"
                print(f"[{timestamp}] {YELLOW}SKIP{RESET} - {item['title'][:60]}...")

        print()
        print("=" * 70)
        print(f"Vinstvarningar hittade: {warnings_found}/{len(swedish_items)}")
        print("=" * 70)

    def monitor_mode(self, poll_interval: float = 30.0):
        """Live monitoring mode."""
        print(f"{BOLD}VINSTVARNING MONITOR - LIVE{RESET}")
        print("=" * 70)
        print(f"Feed: {self.FEED_URL}")
        print(f"Poll interval: {poll_interval}s")
        print(f"Filter: Swedish (SE), Regulatory only")
        print("=" * 70)
        print()

        # Initial fetch to populate seen set
        print("Initialiserar...")
        try:
            items = self.fetch_feed()
            for item in items:
                self._seen_guids.add(item['guid'])
            print(f"Initialiserade med {len(items)} befintliga items")
        except Exception as e:
            print(f"Fel vid initialisering: {e}")

        print()
        print(f"{BOLD}Bevakar feed... (Ctrl+C för att avsluta){RESET}")
        print("-" * 70)

        while True:
            try:
                time.sleep(poll_interval)

                items = self.fetch_feed()
                now = datetime.now().strftime("%H:%M:%S")

                new_items = [i for i in items if i['guid'] not in self._seen_guids]

                if new_items:
                    # Filter Swedish regulatory
                    swedish_new = [i for i in new_items if i['scope'] == 'SE' and i['is_regulatory']]

                    for item in swedish_new:
                        self._seen_guids.add(item['guid'])
                        analysis = self.analyze_item(item)

                        if analysis['result'].is_profit_warning:
                            self.print_alert(analysis)
                        else:
                            print(f"[{now}] Ny nyhet: {item['title'][:50]}... ({YELLOW}ej vinstvarning{RESET})")

                    # Add non-Swedish to seen
                    for item in new_items:
                        self._seen_guids.add(item['guid'])
                else:
                    print(f"[{now}] Inga nya nyheter", end='\r')

            except KeyboardInterrupt:
                print("\n\nAvslutar...")
                break
            except Exception as e:
                print(f"[ERROR] {e}")
                continue


def main():
    parser = argparse.ArgumentParser(description='Vinstvarning Monitor')
    parser.add_argument('--test', action='store_true', help='Test mode - analyze recent feed')
    parser.add_argument('--interval', type=float, default=30, help='Poll interval in seconds')

    args = parser.parse_args()

    monitor = VinstvarningMonitor()

    if args.test:
        monitor.test_mode()
    else:
        monitor.monitor_mode(poll_interval=args.interval)


if __name__ == '__main__':
    main()
