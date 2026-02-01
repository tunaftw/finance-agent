#!/usr/bin/env python3
"""
Run news trading backtest.

This script:
1. Scrapes press releases from MFN (if needed)
2. Filters for profit warnings
3. Matches with price data
4. Simulates trades and calculates returns

Usage:
    python scripts/run_backtest.py                    # Quick test (5 companies)
    python scripts/run_backtest.py --scrape           # Scrape fresh data first
    python scripts/run_backtest.py --companies 20    # Test with 20 companies
    python scripts/run_backtest.py --all              # All known companies
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, 'src')

from podstock.news_trader.backtest.mfn_scraper import MFNScraper
from podstock.news_trader.backtest.engine import BacktestEngine


# Companies to test with (good mix of sizes and sectors)
TEST_COMPANIES = [
    'cheffelo',      # Small cap, meal kits
    'evolution',     # Large cap, gaming
    'sinch',         # Mid cap, communications
    'embracer',      # Mid cap, gaming
    'fortnox',       # Small cap, SaaS
    'boozt',         # Small cap, e-commerce
    'mips',          # Small cap, safety
    'hemnet',        # Mid cap, real estate
    'bioarctic',     # Small cap, biotech
    'kinnevik',      # Mid cap, investment
]

EXTENDED_COMPANIES = TEST_COMPANIES + [
    'investor',      # Large cap, investment
    'volvo',         # Large cap, automotive
    'ericsson',      # Large cap, telecom
    'hexagon',       # Large cap, tech
    'nibe',          # Large cap, climate
    'sectra',        # Mid cap, medtech
    'storytel',      # Small cap, streaming
    'fingerprint',   # Small cap, biometrics
    'vitrolife',     # Mid cap, medtech
    'orexo',         # Small cap, pharma
]


def main():
    parser = argparse.ArgumentParser(description='News Trading Backtest')
    parser.add_argument('--scrape', action='store_true', help='Scrape fresh data from MFN')
    parser.add_argument('--companies', type=int, default=10, help='Number of companies to test')
    parser.add_argument('--all', action='store_true', help='Test all known companies')
    parser.add_argument('--data-file', default='data/backtest/mfn_releases.json', help='Data file path')
    parser.add_argument('--latency', type=int, default=500, help='Assumed latency (ms)')
    parser.add_argument('--slippage', type=float, default=0.5, help='Assumed slippage (%)')
    parser.add_argument('--min-confidence', type=float, default=0.6, help='Min signal confidence')
    parser.add_argument('--rate-limit', type=float, default=0.5, help='Scraping rate limit (seconds)')

    args = parser.parse_args()

    data_path = Path(args.data_file)

    # Determine which companies to use
    if args.all:
        companies = MFNScraper.SWEDISH_COMPANIES
    elif args.companies <= 10:
        companies = TEST_COMPANIES[:args.companies]
    else:
        companies = EXTENDED_COMPANIES[:args.companies]

    print("=" * 70)
    print("VINSTVARNING BACKTEST")
    print("=" * 70)
    print()
    print(f"Bolag:          {len(companies)} st")
    print(f"Latens:         {args.latency} ms")
    print(f"Slippage:       {args.slippage}%")
    print(f"Min confidence: {args.min_confidence}")
    print()

    # Step 1: Get press releases
    if args.scrape or not data_path.exists():
        print("=" * 70)
        print("STEG 1: SCRAPING PRESSMEDDELANDEN")
        print("=" * 70)
        print()

        scraper = MFNScraper(rate_limit_delay=args.rate_limit)
        scraper.scrape_multiple_companies(companies)

        # Filter to Swedish regulatory releases
        swedish_regulatory = [
            r for r in scraper.releases
            if r.scope == 'SE' and r.is_regulatory and r.language == 'sv'
        ]

        print()
        print(f"Totalt scrapad: {len(scraper.releases)} releases")
        print(f"Svenska regulatoriska: {len(swedish_regulatory)} releases")

        # Save
        scraper.releases = swedish_regulatory
        scraper.save_to_json(data_path)
        print()

    # Step 2: Run backtest
    print("=" * 70)
    print("STEG 2: KÖR BACKTEST")
    print("=" * 70)
    print()

    engine = BacktestEngine(
        latency_ms=args.latency,
        slippage_pct=args.slippage,
        exit_strategy="end_of_day",
    )

    engine.load_releases(data_path)
    print(f"Analyserar {len(engine.releases)} pressmeddelanden...")
    print()

    results = engine.run_backtest(
        min_confidence=args.min_confidence,
        verbose=True,
    )

    # Step 3: Print report
    print()
    engine.print_report(results)

    # Step 4: Save results
    results_path = data_path.parent / 'backtest_results.json'
    save_results(results, results_path)
    print(f"\nResultat sparat till: {results_path}")


def save_results(results, filepath: Path):
    """Save backtest results to JSON."""
    import json

    filepath.parent.mkdir(parents=True, exist_ok=True)

    data = {
        'run_at': datetime.now().isoformat(),
        'config': {
            'start_date': results.start_date.isoformat(),
            'end_date': results.end_date.isoformat(),
            'latency_ms': results.latency_ms,
            'slippage_pct': results.slippage_pct,
            'exit_strategy': results.exit_strategy,
        },
        'summary': {
            'total_signals': results.total_signals,
            'trades_executed': results.trades_executed,
            'trades_skipped': results.trades_skipped,
            'winning_trades': results.winning_trades,
            'losing_trades': results.losing_trades,
            'win_rate': results.win_rate,
            'total_return_pct': results.total_return_pct,
            'avg_return_pct': results.avg_return_pct,
            'best_trade_pct': results.best_trade_pct,
            'worst_trade_pct': results.worst_trade_pct,
            'buy_signals': results.buy_signals,
            'sell_signals': results.sell_signals,
        },
        'trades': [
            {
                'date': t.release.pub_datetime.isoformat(),
                'company': t.release.company_slug,
                'ticker': t.ticker,
                'title': t.release.title,
                'signal': t.signal.action,
                'confidence': t.signal.confidence,
                'entry_price': t.entry_price,
                'exit_price': t.exit_price,
                'return_pct': t.return_pct,
            }
            for t in results.trades
        ]
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
