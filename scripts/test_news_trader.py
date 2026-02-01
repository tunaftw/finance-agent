#!/usr/bin/env python3
"""Test the news trader parser against known cases."""

import sys
import time
sys.path.insert(0, 'src')

from podstock.news_trader.parser import PressReleaseParser, Action, Confidence
from podstock.news_trader.feed_monitor import FeedMonitor


def test_parser():
    """Test the parser with known press releases."""
    parser = PressReleaseParser()

    test_cases = [
        # Cheffelo positive surprise (should be STRONG_BUY)
        {
            "name": "Cheffelo omvänd vinstvarning",
            "title": "Cheffelo publicerar preliminär EBIT för fjärde kvartalet till följd av ökat rörelseresultat",
            "description": """Cheffelo, en lönsam skandinavisk leverantör av matkassar, publicerar i dag,
            tidigare än aviserat, en preliminär EBIT för fjärde kvartalet. Det preliminära och ej
            reviderade rörelseresultatet (EBIT) för Q4 2025 uppgår till cirka 36,8 MSEK (29.4) vilket
            motsvarar en ökning med cirka 7,4 MSEK jämfört med Q4 2024.""",
            "expected_action": Action.STRONG_BUY,
        },
        # Negative profit warning (should be SELL/STRONG_SELL)
        {
            "name": "Negativ vinstvarning",
            "title": "ABC AB sänker prognos för helåret",
            "description": """ABC AB meddelar idag att bolaget reviderar sin helårsprognos.
            Rörelseresultatet förväntas uppgå till 15 MSEK (25) vilket är lägre än tidigare
            kommunicerat. Nedgången beror på svagare efterfrågan.""",
            "expected_action": Action.STRONG_SELL,
        },
        # Acquisition news (should be BUY with lower confidence)
        {
            "name": "Förvärv",
            "title": "XYZ AB förvärvar konkurrent för 100 MSEK",
            "description": """XYZ AB har ingått avtal om att förvärva DEF AB för 100 MSEK.
            Förvärvet förväntas stärka bolagets marknadsposition och öka omsättningen.""",
            "expected_action": Action.BUY,
        },
        # Insider buy (positive signal)
        {
            "name": "Insynshandel - köp",
            "title": "Insynshandel: VD köper aktier för 500 000 kr",
            "description": """VD Johan Johansson har förvärvat 10 000 aktier i bolaget
            till kursen 50 kr per aktie.""",
            "expected_action": Action.BUY,
        },
        # Neutral quarterly report
        {
            "name": "Neutral kvartalsrapport",
            "title": "Kvartalsrapport Q3 2025",
            "description": """Bolaget rapporterar omsättning om 100 MSEK (98) och
            rörelseresultat om 10 MSEK (10,5). Resultatet är i linje med förväntan.""",
            "expected_action": Action.HOLD,
        },
    ]

    print("=" * 70)
    print("PARSER TEST SUITE")
    print("=" * 70)

    passed = 0
    failed = 0

    for i, case in enumerate(test_cases, 1):
        start = time.perf_counter()
        signal = parser.analyze(case["title"], case["description"])
        elapsed = (time.perf_counter() - start) * 1000

        # Check if action matches expectation (allow STRONG variants)
        action_matches = (
            signal.action == case["expected_action"] or
            (signal.action == Action.STRONG_BUY and case["expected_action"] == Action.BUY) or
            (signal.action == Action.BUY and case["expected_action"] == Action.STRONG_BUY) or
            (signal.action == Action.STRONG_SELL and case["expected_action"] == Action.SELL) or
            (signal.action == Action.SELL and case["expected_action"] == Action.STRONG_SELL)
        )

        status = "✅ PASS" if action_matches else "❌ FAIL"
        if action_matches:
            passed += 1
        else:
            failed += 1

        print(f"\nTest {i}: {case['name']}")
        print(f"  Title: {case['title'][:50]}...")
        print(f"  Expected: {case['expected_action'].value}")
        print(f"  Got: {signal.action.value} ({signal.confidence.value})")
        print(f"  Reason: {signal.reason}")
        print(f"  Time: {elapsed:.2f} ms")
        print(f"  Status: {status}")

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed}/{len(test_cases)} passed")
    print("=" * 70)


def test_live_feed():
    """Test fetching and parsing the live MFN feed."""
    print("\n" + "=" * 70)
    print("LIVE FEED TEST")
    print("=" * 70)

    monitor = FeedMonitor(
        filter_countries=['SE'],
        filter_regulatory_only=True,
        min_confidence='LOW',
    )

    print(f"Fetching {monitor.feed_url}...")
    start = time.perf_counter()

    try:
        items = monitor.fetch_feed()
        fetch_time = (time.perf_counter() - start) * 1000

        print(f"Fetched {len(items)} items in {fetch_time:.0f} ms")
        print()

        # Process first 5 Swedish regulatory items
        swedish_items = [i for i in items if i.scope == 'SE' and i.is_regulatory][:5]

        print(f"Processing {len(swedish_items)} Swedish regulatory items:")
        print("-" * 70)

        for item in swedish_items:
            start = time.perf_counter()
            signal = monitor.process_item(item)
            elapsed = (time.perf_counter() - start) * 1000

            if signal:
                color = '\033[92m' if signal.action in [Action.BUY, Action.STRONG_BUY] else \
                        '\033[91m' if signal.action in [Action.SELL, Action.STRONG_SELL] else '\033[93m'
                reset = '\033[0m'

                timestamp = item.pub_datetime.strftime("%Y-%m-%d %H:%M") if item.pub_datetime else "Unknown"

                print(f"\n[{timestamp}] {color}{signal.action.value}{reset}")
                print(f"  Title: {item.title[:60]}...")
                print(f"  Reason: {signal.reason}")
                print(f"  Confidence: {signal.confidence.value}")
                print(f"  Analysis time: {elapsed:.2f} ms")

    except Exception as e:
        print(f"Error: {e}")
        raise


def benchmark():
    """Benchmark parser performance."""
    print("\n" + "=" * 70)
    print("PERFORMANCE BENCHMARK")
    print("=" * 70)

    parser = PressReleaseParser()

    # Sample text
    title = "Cheffelo publicerar preliminär EBIT för fjärde kvartalet"
    desc = """Det preliminära rörelseresultatet för Q4 2025 uppgår till cirka 36,8 MSEK (29.4)."""

    # Warmup
    for _ in range(100):
        parser.analyze(title, desc)

    # Benchmark
    iterations = 10000
    start = time.perf_counter()
    for _ in range(iterations):
        parser.analyze(title, desc)
    elapsed = time.perf_counter() - start

    avg_time = (elapsed / iterations) * 1000  # ms
    throughput = iterations / elapsed

    print(f"Iterations: {iterations}")
    print(f"Total time: {elapsed:.2f} s")
    print(f"Average time per analysis: {avg_time:.4f} ms")
    print(f"Throughput: {throughput:.0f} analyses/second")


if __name__ == '__main__':
    test_parser()
    test_live_feed()
    benchmark()
