"""Backtesting engine for news trading strategies.

Combines press releases with price data to simulate trading performance.

Example usage::

    from podstock.news_trader.backtest.engine import BacktestEngine

    engine = BacktestEngine()
    engine.load_releases("data/mfn_releases.json")
    results = engine.run_backtest()
    engine.print_report(results)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import time

import yfinance as yf

from podstock.news_trader.vinstvarning_detector import (
    VinstvarningDetector,
    VinstvarningResult,
)
from podstock.news_trader.backtest.mfn_scraper import PressRelease, MFNScraper


@dataclass
class Trade:
    """A simulated trade."""
    release: PressRelease
    signal: VinstvarningResult

    # Trade execution
    ticker: str
    entry_time: datetime
    entry_price: float
    exit_time: datetime
    exit_price: float

    # Results
    return_pct: float
    holding_period_minutes: int

    # Metadata
    latency_assumed_ms: int
    slippage_assumed_pct: float


@dataclass
class BacktestResults:
    """Results from a backtest run."""
    # Configuration
    start_date: datetime
    end_date: datetime
    latency_ms: int
    slippage_pct: float
    exit_strategy: str  # "end_of_day", "next_open", "fixed_minutes"

    # Trade statistics
    total_signals: int = 0
    trades_executed: int = 0
    trades_skipped: int = 0  # No price data available

    # Performance
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0

    total_return_pct: float = 0.0
    avg_return_pct: float = 0.0
    best_trade_pct: float = 0.0
    worst_trade_pct: float = 0.0

    # By signal type
    buy_signals: int = 0
    sell_signals: int = 0
    buy_return_pct: float = 0.0
    sell_return_pct: float = 0.0

    # Trade list
    trades: list[Trade] = field(default_factory=list)


# Mapping from company slug to Yahoo Finance ticker
COMPANY_TICKER_MAP = {
    # Large cap
    'investor': 'INVE-B.ST',
    'volvo': 'VOLV-B.ST',
    'ericsson': 'ERIC-B.ST',
    'atlas-copco': 'ATCO-A.ST',
    'abb': 'ABB.ST',
    'sandvik': 'SAND.ST',
    'seb': 'SEB-A.ST',
    'handelsbanken': 'SHB-A.ST',
    'nordea': 'NDA-SE.ST',
    'swedbank': 'SWED-A.ST',
    'hm': 'HM-B.ST',
    'assa-abloy': 'ASSA-B.ST',
    'hexagon': 'HEXA-B.ST',
    'alfa-laval': 'ALFA.ST',
    'skf': 'SKF-B.ST',
    'electrolux': 'ELUX-B.ST',
    'essity': 'ESSITY-B.ST',
    'telia': 'TELIA.ST',
    'epiroc': 'EPI-A.ST',
    'nibe': 'NIBE-B.ST',
    'evolution': 'EVO.ST',
    'spotify': 'SPOT',  # US listed

    # Mid cap
    'cheffelo': 'CHEF.ST',
    'sinch': 'SINCH.ST',
    'embracer': 'EMBRAC-B.ST',
    'stillfront': 'SF.ST',
    'paradox-interactive': 'PDX.ST',
    'thule': 'THULE.ST',
    'addlife': 'ADDL-B.ST',
    'addtech': 'ADDT-B.ST',
    'beijer-ref': 'BEIJ-B.ST',
    'bufab': 'BUFAB.ST',
    'bravida': 'BRAV.ST',
    'coor': 'COOR.ST',
    'dometic': 'DOM.ST',
    'fagerhult': 'FAG.ST',
    'hexpol': 'HPOL-B.ST',
    'indutrade': 'INDT.ST',
    'intrum': 'INTRUM.ST',
    'kinnevik': 'KINV-B.ST',
    'latour': 'LATO-B.ST',
    'lifco': 'LIFCO-B.ST',
    'loomis': 'LOOM-B.ST',
    'medicover': 'MCOV-B.ST',
    'munters': 'MTRS.ST',
    'ncc': 'NCC-B.ST',
    'peab': 'PEAB-B.ST',
    'saab': 'SAAB-B.ST',
    'securitas': 'SECU-B.ST',
    'skanska': 'SKA-B.ST',
    'ssab': 'SSAB-A.ST',
    'sweco': 'SWEC-B.ST',
    'trelleborg': 'TREL-B.ST',
    'vitrolife': 'VITR.ST',
    'wihlborgs': 'WIHL.ST',

    # Small cap / First North
    'bico': 'BICO.ST',
    'bioarctic': 'BIOA-B.ST',
    'boozt': 'BOOZT.ST',
    'catena': 'CATE.ST',
    'collector': 'COLL.ST',
    'fingerprint': 'FING-B.ST',
    'fortnox': 'FNOX.ST',
    'hemnet': 'HEM.ST',
    'mips': 'MIPS.ST',
    'netent': 'NET-B.ST',
    'orexo': 'ORX.ST',
    'sectra': 'SECT-B.ST',
    'storytel': 'STORY-B.ST',
    'tobii': 'TOBII.ST',
}


class BacktestEngine:
    """Engine for backtesting news trading strategies."""

    def __init__(
        self,
        latency_ms: int = 500,
        slippage_pct: float = 0.5,
        exit_strategy: str = "end_of_day",
        exit_minutes: int = 60,
    ):
        """Initialize backtesting engine.

        Args:
            latency_ms: Assumed latency from news to trade execution
            slippage_pct: Assumed slippage on entry (as percentage)
            exit_strategy: "end_of_day", "next_open", or "fixed_minutes"
            exit_minutes: Minutes to hold (if exit_strategy="fixed_minutes")
        """
        self.latency_ms = latency_ms
        self.slippage_pct = slippage_pct
        self.exit_strategy = exit_strategy
        self.exit_minutes = exit_minutes

        self.detector = VinstvarningDetector()
        self.releases: list[PressRelease] = []
        self._price_cache: dict[str, dict] = {}

    def load_releases(self, filepath: str | Path) -> list[PressRelease]:
        """Load press releases from JSON file."""
        scraper = MFNScraper()
        self.releases = scraper.load_from_json(filepath)
        return self.releases

    def get_ticker(self, company_slug: str) -> Optional[str]:
        """Get Yahoo Finance ticker for company."""
        return COMPANY_TICKER_MAP.get(company_slug)

    def get_intraday_prices(
        self,
        ticker: str,
        date: datetime,
    ) -> Optional[dict]:
        """Get intraday minute prices for a date.

        Returns dict with minute timestamps as keys and OHLCV as values.
        """
        cache_key = f"{ticker}_{date.date()}"
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]

        try:
            yf_ticker = yf.Ticker(ticker)

            # Yahoo needs a range for intraday data
            start = datetime(date.year, date.month, date.day)
            end = start + timedelta(days=1)

            hist = yf_ticker.history(start=start, end=end, interval='1m')

            if hist.empty:
                return None

            # Convert to dict with minute keys
            prices = {}
            for idx, row in hist.iterrows():
                minute_key = idx.strftime("%H:%M")
                prices[minute_key] = {
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']),
                }

            self._price_cache[cache_key] = prices
            return prices

        except Exception as e:
            print(f"Error fetching prices for {ticker}: {e}")
            return None

    def get_daily_prices(
        self,
        ticker: str,
        date: datetime,
    ) -> Optional[dict]:
        """Get daily OHLCV for a date."""
        try:
            yf_ticker = yf.Ticker(ticker)

            start = date - timedelta(days=5)
            end = date + timedelta(days=2)

            hist = yf_ticker.history(start=start, end=end)

            if hist.empty:
                return None

            # Find the specific date
            target_date = date.date()
            for idx, row in hist.iterrows():
                if idx.date() == target_date:
                    return {
                        'open': float(row['Open']),
                        'high': float(row['High']),
                        'low': float(row['Low']),
                        'close': float(row['Close']),
                        'volume': int(row['Volume']),
                    }

            return None

        except Exception as e:
            print(f"Error fetching daily prices for {ticker}: {e}")
            return None

    def simulate_trade(
        self,
        release: PressRelease,
        signal: ProfitWarningResult,
        ticker: str,
    ) -> Optional[Trade]:
        """Simulate a single trade.

        Args:
            release: The press release
            signal: The trading signal
            ticker: Yahoo Finance ticker

        Returns:
            Trade object if successful, None if no price data
        """
        pub_time = release.pub_datetime

        # Calculate entry time (publication + latency)
        entry_time = pub_time + timedelta(milliseconds=self.latency_ms)
        entry_minute = entry_time.strftime("%H:%M")

        # Get intraday prices
        prices = self.get_intraday_prices(ticker, pub_time)

        if not prices:
            # Fall back to daily data
            daily = self.get_daily_prices(ticker, pub_time)
            if not daily:
                return None

            # Use daily open as entry (conservative)
            entry_price = daily['open']
            exit_price = daily['close']

            # Apply slippage
            if signal.action in ["BUY", "STRONG_BUY"]:
                entry_price *= (1 + self.slippage_pct / 100)
            else:
                entry_price *= (1 - self.slippage_pct / 100)

            # Calculate return
            if signal.action in ["BUY", "STRONG_BUY"]:
                return_pct = ((exit_price - entry_price) / entry_price) * 100
            else:  # SELL signal = short
                return_pct = ((entry_price - exit_price) / entry_price) * 100

            return Trade(
                release=release,
                signal=signal,
                ticker=ticker,
                entry_time=entry_time,
                entry_price=entry_price,
                exit_time=pub_time.replace(hour=17, minute=30),  # Market close
                exit_price=exit_price,
                return_pct=return_pct,
                holding_period_minutes=int((17.5 - pub_time.hour) * 60),
                latency_assumed_ms=self.latency_ms,
                slippage_assumed_pct=self.slippage_pct,
            )

        # Find entry price at entry minute
        entry_price = None
        for minute, data in sorted(prices.items()):
            if minute >= entry_minute:
                entry_price = data['close']  # Use close of that minute
                actual_entry_minute = minute
                break

        if entry_price is None:
            # Entry time is after market hours
            return None

        # Apply slippage
        if signal.action in ["BUY", "STRONG_BUY"]:
            entry_price *= (1 + self.slippage_pct / 100)
        else:
            entry_price *= (1 - self.slippage_pct / 100)

        # Find exit price based on strategy
        if self.exit_strategy == "end_of_day":
            # Use last available price
            last_minute = max(prices.keys())
            exit_price = prices[last_minute]['close']
            exit_minute = last_minute
        elif self.exit_strategy == "fixed_minutes":
            # Exit after fixed time
            exit_time = entry_time + timedelta(minutes=self.exit_minutes)
            exit_minute = exit_time.strftime("%H:%M")

            # Find closest available minute
            exit_price = None
            for minute, data in sorted(prices.items()):
                if minute >= exit_minute:
                    exit_price = data['close']
                    exit_minute = minute
                    break

            if exit_price is None:
                # Exit time after market, use EOD
                last_minute = max(prices.keys())
                exit_price = prices[last_minute]['close']
                exit_minute = last_minute
        else:
            # Default to EOD
            last_minute = max(prices.keys())
            exit_price = prices[last_minute]['close']
            exit_minute = last_minute

        # Calculate return
        if signal.action in ["BUY", "STRONG_BUY"]:
            return_pct = ((exit_price - entry_price) / entry_price) * 100
        else:  # SELL/SHORT signal
            return_pct = ((entry_price - exit_price) / entry_price) * 100

        # Calculate holding period
        entry_minutes = int(actual_entry_minute.split(':')[0]) * 60 + int(actual_entry_minute.split(':')[1])
        exit_minutes = int(exit_minute.split(':')[0]) * 60 + int(exit_minute.split(':')[1])
        holding_period = exit_minutes - entry_minutes

        return Trade(
            release=release,
            signal=signal,
            ticker=ticker,
            entry_time=entry_time,
            entry_price=entry_price,
            exit_time=pub_time.replace(
                hour=int(exit_minute.split(':')[0]),
                minute=int(exit_minute.split(':')[1])
            ),
            exit_price=exit_price,
            return_pct=return_pct,
            holding_period_minutes=holding_period,
            latency_assumed_ms=self.latency_ms,
            slippage_assumed_pct=self.slippage_pct,
        )

    def run_backtest(
        self,
        releases: Optional[list[PressRelease]] = None,
        filter_regulatory: bool = True,
        filter_swedish: bool = True,
        min_confidence: float = 0.6,
        verbose: bool = True,
    ) -> BacktestResults:
        """Run backtest on press releases.

        Args:
            releases: Releases to backtest (defaults to self.releases)
            filter_regulatory: Only include regulatory releases
            filter_swedish: Only include Swedish releases
            min_confidence: Minimum signal confidence to trade
            verbose: Print progress

        Returns:
            BacktestResults with all statistics
        """
        releases = releases or self.releases

        # Apply filters
        if filter_regulatory:
            releases = [r for r in releases if r.is_regulatory]
        if filter_swedish:
            releases = [r for r in releases if r.scope == "SE"]

        # Sort by date
        releases = sorted(releases, key=lambda r: r.pub_datetime)

        if not releases:
            print("No releases to backtest!")
            return BacktestResults(
                start_date=datetime.now(),
                end_date=datetime.now(),
                latency_ms=self.latency_ms,
                slippage_pct=self.slippage_pct,
                exit_strategy=self.exit_strategy,
            )

        results = BacktestResults(
            start_date=releases[0].pub_datetime,
            end_date=releases[-1].pub_datetime,
            latency_ms=self.latency_ms,
            slippage_pct=self.slippage_pct,
            exit_strategy=self.exit_strategy,
        )

        trades = []

        for i, release in enumerate(releases):
            if verbose and i % 10 == 0:
                print(f"Processing {i+1}/{len(releases)}...", end='\r')

            # Analyze for profit warning
            signal = self.detector.analyze(release.title, release.description)

            # Skip if not a profit warning or low confidence
            if not signal.is_profit_warning or signal.confidence < min_confidence:
                continue

            results.total_signals += 1

            if signal.action in ["BUY", "STRONG_BUY"]:
                results.buy_signals += 1
            elif signal.action in ["SELL", "STRONG_SELL"]:
                results.sell_signals += 1
            else:
                continue  # Skip HOLD signals

            # Get ticker
            ticker = self.get_ticker(release.company_slug)
            if not ticker:
                results.trades_skipped += 1
                continue

            # Simulate trade
            trade = self.simulate_trade(release, signal, ticker)

            if trade is None:
                results.trades_skipped += 1
                continue

            trades.append(trade)
            results.trades_executed += 1

            if trade.return_pct > 0:
                results.winning_trades += 1
            else:
                results.losing_trades += 1

            if signal.action in ["BUY", "STRONG_BUY"]:
                results.buy_return_pct += trade.return_pct
            else:
                results.sell_return_pct += trade.return_pct

        if verbose:
            print()  # Clear progress line

        # Calculate aggregate stats
        results.trades = trades

        if trades:
            results.total_return_pct = sum(t.return_pct for t in trades)
            results.avg_return_pct = results.total_return_pct / len(trades)
            results.best_trade_pct = max(t.return_pct for t in trades)
            results.worst_trade_pct = min(t.return_pct for t in trades)
            results.win_rate = results.winning_trades / len(trades) if trades else 0

        return results

    def print_report(self, results: BacktestResults):
        """Print a formatted backtest report."""
        GREEN = '\033[92m'
        RED = '\033[91m'
        YELLOW = '\033[93m'
        BOLD = '\033[1m'
        RESET = '\033[0m'

        print()
        print(f"{BOLD}{'='*70}{RESET}")
        print(f"{BOLD}BACKTEST RAPPORT - VINSTVARNING TRADING{RESET}")
        print(f"{'='*70}")
        print()

        print(f"{BOLD}Konfiguration:{RESET}")
        print(f"  Period:        {results.start_date.date()} till {results.end_date.date()}")
        print(f"  Latens:        {results.latency_ms} ms")
        print(f"  Slippage:      {results.slippage_pct}%")
        print(f"  Exit-strategi: {results.exit_strategy}")
        print()

        print(f"{BOLD}Signaler:{RESET}")
        print(f"  Totalt:        {results.total_signals}")
        print(f"  - Köpsignaler: {results.buy_signals}")
        print(f"  - Säljsignaler:{results.sell_signals}")
        print()

        print(f"{BOLD}Trades:{RESET}")
        print(f"  Genomförda:    {results.trades_executed}")
        print(f"  Skippade:      {results.trades_skipped} (ingen prisdata)")
        print()

        if results.trades_executed > 0:
            print(f"{BOLD}Resultat:{RESET}")
            color = GREEN if results.total_return_pct > 0 else RED
            print(f"  Total avkastning:  {color}{results.total_return_pct:+.2f}%{RESET}")
            print(f"  Snitt per trade:   {color}{results.avg_return_pct:+.2f}%{RESET}")
            print(f"  Win rate:          {results.win_rate:.1%}")
            print(f"  Vinnande trades:   {results.winning_trades}")
            print(f"  Förlorande trades: {results.losing_trades}")
            print()

            print(f"{BOLD}Extremer:{RESET}")
            print(f"  Bästa trade:   {GREEN}{results.best_trade_pct:+.2f}%{RESET}")
            print(f"  Sämsta trade:  {RED}{results.worst_trade_pct:+.2f}%{RESET}")
            print()

            if results.buy_signals > 0:
                buy_avg = results.buy_return_pct / results.buy_signals if results.buy_signals else 0
                color = GREEN if buy_avg > 0 else RED
                print(f"  Köpsignaler snitt: {color}{buy_avg:+.2f}%{RESET}")

            if results.sell_signals > 0:
                sell_avg = results.sell_return_pct / results.sell_signals if results.sell_signals else 0
                color = GREEN if sell_avg > 0 else RED
                print(f"  Säljsignaler snitt: {color}{sell_avg:+.2f}%{RESET}")

        print()
        print(f"{'='*70}")

        # Print individual trades
        if results.trades:
            print()
            print(f"{BOLD}INDIVIDUELLA TRADES:{RESET}")
            print("-" * 70)
            print(f"{'Datum':<12} {'Bolag':<15} {'Signal':<12} {'Entry':>8} {'Exit':>8} {'Return':>8}")
            print("-" * 70)

            for trade in sorted(results.trades, key=lambda t: t.release.pub_datetime):
                date_str = trade.release.pub_datetime.strftime("%Y-%m-%d")
                company = trade.release.company_slug[:14]
                signal = trade.signal.action
                entry = f"{trade.entry_price:.2f}"
                exit_p = f"{trade.exit_price:.2f}"

                color = GREEN if trade.return_pct > 0 else RED
                return_str = f"{color}{trade.return_pct:+.2f}%{RESET}"

                print(f"{date_str:<12} {company:<15} {signal:<12} {entry:>8} {exit_p:>8} {return_str:>8}")

            print("-" * 70)


def main():
    """Run backtest from command line."""
    import argparse

    parser = argparse.ArgumentParser(description='News Trading Backtester')
    parser.add_argument('--input', default='data/mfn_releases.json', help='Input releases file')
    parser.add_argument('--latency', type=int, default=500, help='Latency in ms')
    parser.add_argument('--slippage', type=float, default=0.5, help='Slippage percentage')
    parser.add_argument('--exit', choices=['end_of_day', 'fixed_minutes'], default='end_of_day')
    parser.add_argument('--exit-minutes', type=int, default=60, help='Minutes to hold')

    args = parser.parse_args()

    engine = BacktestEngine(
        latency_ms=args.latency,
        slippage_pct=args.slippage,
        exit_strategy=args.exit,
        exit_minutes=args.exit_minutes,
    )

    engine.load_releases(args.input)
    results = engine.run_backtest()
    engine.print_report(results)


if __name__ == '__main__':
    main()
