#!/usr/bin/env python3
"""Fact-check @alexeliasson's Twitter investment picks against actual price data.

Reads tweets from data/twitter/raw/alexeliasson/tweets.jsonl, identifies
actionable investment calls, fetches price data from Yahoo Finance, and
calculates returns at various intervals.
"""

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import yfinance as yf

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


# ── Manually curated investment calls ──────────────────────────────────────
# Each entry: (tweet_date, yahoo_ticker, direction, description, tweet_id)
# Only includes tweets where he clearly takes a position or recommends buying.
# Excludes pure news/commentary tweets.

INVESTMENT_CALLS = [
    # 2024 picks
    ("2024-02-07", "DNO.OL", "bull", "Iraq pipeline reopening thesis, DNO", "1755165968811094137"),
    ("2024-04-08", "SNM.ST", "bull", "Shamaran - best asymmetric risk proposition", "1777289785859801211"),
    ("2024-04-08", "GKP.L", "bull", "Gulf Keystone - best asymmetric risk proposition", "1777289785859801211"),
    ("2024-04-08", "DNO.OL", "bull", "DNO - best asymmetric risk proposition", "1777289785859801211"),
    ("2024-04-03", "HSBK", "bull", "Halyk ATH, +100% 1Y, p/e 2.8x, still top holding", "1775441758324961461"),
    ("2024-05-30", "SEPL.L", "bull", "Seplat - largest holding, set to triple net profit", "1796182995616854224"),
    ("2024-06-21", "GKP.L", "bull", "GKP restarts dividends, 20% FCF yield", "1804097868296581304"),
    ("2024-07-07", "HEPS", "bull", "Hepsiburada - new position, fastest growing ecom", "1809887735366443294"),
    # 2025 picks
    ("2025-01-02", "EVO.ST", "bull", "Evolution - sizeable position, valuation near IPO-lows", "1874781999816405175"),
    ("2025-01-16", "XP", "bull", "XP Inc - new position, ~7x p/e, IPO-lows", "1879912832189464997"),
    ("2025-01-28", "CPALL.BK", "bull", "7-Eleven Thailand - 5-year low, probably a buy", "1884224984576581807"),
    ("2025-01-29", "IMAX", "bull", "IMAX - 50% global market share, asset-light", "1884632892015554901"),
    ("2025-02-04", "SPRC.BK", "bull", "SPRC Thailand - 25% FCF yield, silly cheap, bought", "1886838154105381205"),
    ("2025-02-15", "3673.T", "bull", "Broadleaf Japan - SaaS inflection, <3x sales", "1890801339971563531"),
    ("2025-03-13", "CSH.DE", "bull", "Cenit (German Addnode) - taken position", "1900199051209199862"),
    ("2025-03-24", "WMA.CO", "bull", "WindowMaster - long, growing fast in USA", "1904111875929031055"),
    ("2025-03-26", "WATR.L", "bull", "Water Intelligence - long @ 3.5 GBP", "1904894177697308922"),
    ("2025-04-20", "8715.T", "bull", "Anicom - #1 Pet Insurance Japan, 10y-low valuation", "1913945000657948814"),
    ("2025-04-24", "FTK.DE", "bull", "FlatexDegiro - long runway, Germans under-allocated", "1915381895367651476"),
    ("2025-05-08", "LOGO.IS", "bull", "LOGO Turkey - buybacks, 10x dividend", "1920376229225521275"),
    ("2025-05-11", "1970.HK", "bull", "IMAX China - revenue +90%, net profit +172%", "1921540103941366127"),
    ("2025-05-13", "NETBAY.BK", "bull", "Netbay Thailand - market leading B2B SaaS, 16x p/e", "1922273805621186803"),
    ("2025-05-15", "SEI.BK", "bull", "SEI Medical Thailand - net profit +405%, largest foreign holder", "1923014088788967818"),
    ("2025-05-29", "FUTU", "bull", "FUTU Q1 - revenue +81%, net profit +97%", "1928019207364694178"),
    ("2025-07-09", "AOJ-B.CO", "bull", "AOJ bought at 87 DKK", "1942818432065626143"),
    ("2025-07-10", "GXI.DE", "bull", "Gerresheimer - slaughtered -50%, deep value", "1943234391024767382"),
    ("2025-07-20", "TIGR", "bull", "Tiger Brokers - P/E 12x too cheap, Q1 thread", "1946903652297494538"),
    ("2025-08-07", "CCIR", "bull", "Kyivstar SPAC - Ukraine pure-play, 3.9x ev/ebitda", "1953367973575700634"),
    ("2025-08-07", "HUMAN.BK", "bull", "HUMAN.bk Thailand SaaS - rolling into from Netbay", "1953420461263523858"),
    ("2025-12-23", "GMS.L", "bull", "Gulf Marine Services - 35% FCF yield, maiden dividend", "2003398989337809146"),
    # 2026 picks (from new tweets downloaded 2026-02-05)
    ("2026-01-01", "SAV.BK", "bull", "Samart Aviation - monopoly ATC Thailand, 9x FCF, 8% div", ""),
    ("2026-01-01", "BET.BD", "bull", "Budapest Stock Exchange - 2 monopolies, $80m EV", ""),
    ("2026-01-01", "CAPD.L", "bull", "Capital Ltd - mining services/labs, profit recycling", ""),
    ("2026-01-01", "ANG.AX", "bull", "Austin Engineering - mining equipment, gold tailwinds", ""),
    ("2026-01-01", "0975.HK", "bull", "Mongolia Mining Corp - gold producer, 5x earnings", ""),
    ("2026-01-09", "BCP.BK", "bull", "Bangchak refinery Thailand - entry 28, Maybank +80% upside", ""),
    ("2026-01-21", "ERD.TO", "bull", "Erdene Resource - gold Mongolia, increased position", ""),
    ("2026-02-02", "KLAR", "bull", "Klarna - position taken at $22.7", ""),
    ("2026-02-05", "FOUR", "bull", "Shift4 Payments - accumulating", ""),
]


def fetch_price_at_date(ticker: str, date: datetime) -> float | None:
    """Fetch closing price for ticker on or near a specific date."""
    try:
        t = yf.Ticker(ticker)
        start = date - timedelta(days=7)
        end = date + timedelta(days=3)
        hist = t.history(start=start, end=end)
        if hist.empty:
            return None
        target = date.date()
        matching = [d.date() for d in hist.index if d.date() <= target]
        if not matching:
            # Take earliest available
            matching = [d.date() for d in hist.index]
        closest = max(matching) if matching else min(d.date() for d in hist.index)
        row = hist.loc[hist.index.date == closest]
        if row.empty:
            return None
        return float(row["Close"].iloc[0])
    except Exception as e:
        print(f"  [WARN] Could not fetch {ticker} at {date.date()}: {e}")
        return None


def fetch_current_price(ticker: str) -> tuple[float | None, str | None]:
    """Fetch current/latest price for ticker. Returns (price, date_str)."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if hist.empty:
            return None, None
        price = float(hist["Close"].iloc[-1])
        date_str = hist.index[-1].strftime("%Y-%m-%d")
        return price, date_str
    except Exception as e:
        print(f"  [WARN] Could not fetch current price for {ticker}: {e}")
        return None, None


def fetch_price_after_days(ticker: str, base_date: datetime, days: int) -> float | None:
    """Fetch price N days after base_date."""
    target = base_date + timedelta(days=days)
    if target > datetime.now():
        return None
    return fetch_price_at_date(ticker, target)


def calc_return(entry: float | None, exit_: float | None) -> float | None:
    """Calculate percentage return."""
    if entry is None or exit_ is None or entry == 0:
        return None
    return ((exit_ - entry) / entry) * 100


def main():
    print("=" * 90)
    print("FACT-CHECK: @alexeliasson Twitter Investment Picks")
    print("=" * 90)
    print()

    results = []

    for i, (date_str, ticker, direction, desc, tweet_id) in enumerate(INVESTMENT_CALLS):
        tweet_date = datetime.strptime(date_str, "%Y-%m-%d")
        print(f"[{i+1}/{len(INVESTMENT_CALLS)}] {ticker} ({date_str}) - {desc}")

        time.sleep(0.6)  # Rate limit

        entry_price = fetch_price_at_date(ticker, tweet_date)
        if entry_price is None:
            print(f"  -> SKIP: Could not get entry price")
            results.append({
                "date": date_str,
                "ticker": ticker,
                "direction": direction,
                "description": desc,
                "entry_price": None,
                "error": "No entry price",
            })
            continue

        time.sleep(0.6)

        # Fetch prices at intervals
        price_1w = fetch_price_after_days(ticker, tweet_date, 7)
        time.sleep(0.4)
        price_1m = fetch_price_after_days(ticker, tweet_date, 30)
        time.sleep(0.4)
        price_3m = fetch_price_after_days(ticker, tweet_date, 90)
        time.sleep(0.4)
        current_price, current_date = fetch_current_price(ticker)

        ret_1w = calc_return(entry_price, price_1w)
        ret_1m = calc_return(entry_price, price_1m)
        ret_3m = calc_return(entry_price, price_3m)
        ret_current = calc_return(entry_price, current_price)

        result = {
            "date": date_str,
            "ticker": ticker,
            "direction": direction,
            "description": desc,
            "tweet_id": tweet_id,
            "entry_price": entry_price,
            "price_1w": price_1w,
            "price_1m": price_1m,
            "price_3m": price_3m,
            "current_price": current_price,
            "current_date": current_date,
            "return_1w": ret_1w,
            "return_1m": ret_1m,
            "return_3m": ret_3m,
            "return_current": ret_current,
        }
        results.append(result)

        ret_str = f"1w:{ret_1w:+.1f}%" if ret_1w is not None else "1w:N/A"
        ret_str += f"  1m:{ret_1m:+.1f}%" if ret_1m is not None else "  1m:N/A"
        ret_str += f"  3m:{ret_3m:+.1f}%" if ret_3m is not None else "  3m:N/A"
        ret_str += f"  now:{ret_current:+.1f}%" if ret_current is not None else "  now:N/A"
        print(f"  Entry: {entry_price:.2f} | {ret_str}")

    # ── Summary ─────────────────────────────────────────────────────────────
    print()
    print("=" * 90)
    print("RESULTS TABLE")
    print("=" * 90)
    print()

    header = f"{'Date':<12} {'Ticker':<12} {'Entry':>8} {'1W':>8} {'1M':>8} {'3M':>8} {'Current':>8} {'Cur.Date':<12} {'Description'}"
    print(header)
    print("-" * len(header))

    valid_results = [r for r in results if r.get("entry_price") is not None]

    for r in valid_results:
        def fmt_ret(v):
            return f"{v:+.1f}%" if v is not None else "N/A"

        print(
            f"{r['date']:<12} {r['ticker']:<12} {r['entry_price']:>8.2f} "
            f"{fmt_ret(r.get('return_1w')):>8} {fmt_ret(r.get('return_1m')):>8} "
            f"{fmt_ret(r.get('return_3m')):>8} {fmt_ret(r.get('return_current')):>8} "
            f"{r.get('current_date', 'N/A'):<12} {r['description'][:40]}"
        )

    # ── Aggregate Stats ─────────────────────────────────────────────────────
    print()
    print("=" * 90)
    print("AGGREGATE STATISTICS")
    print("=" * 90)

    for interval_name, key in [("1 Week", "return_1w"), ("1 Month", "return_1m"),
                                ("3 Months", "return_3m"), ("Current", "return_current")]:
        returns = [r[key] for r in valid_results if r.get(key) is not None]
        if not returns:
            continue
        winners = [r for r in returns if r > 0]
        losers = [r for r in returns if r <= 0]
        avg = sum(returns) / len(returns)
        median = sorted(returns)[len(returns) // 2]
        best = max(returns)
        worst = min(returns)
        win_rate = len(winners) / len(returns) * 100

        print(f"\n{interval_name} ({len(returns)} picks with data):")
        print(f"  Win Rate:    {win_rate:.0f}% ({len(winners)}/{len(returns)})")
        print(f"  Avg Return:  {avg:+.1f}%")
        print(f"  Median:      {median:+.1f}%")
        print(f"  Best:        {best:+.1f}%")
        print(f"  Worst:       {worst:+.1f}%")

    # ── Save results ────────────────────────────────────────────────────────
    output_path = PROJECT_ROOT / "data" / "twitter" / "analyses" / "alexeliasson_factcheck.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({"generated_at": datetime.now().isoformat(), "results": results}, f, indent=2, default=str)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
