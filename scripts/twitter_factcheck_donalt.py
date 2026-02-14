#!/usr/bin/env python3
"""Fact-check @CryptoDonAlt's Twitter trading calls against actual price data.

Phase 1: Extract all potential signal tweets from the JSONL data.
Phase 2: Classify and extract structured trading signals.
Phase 3: Fetch crypto prices and calculate performance.
"""

from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Crypto ticker mapping ───────────────────────────────────────────────────
# Maps common crypto mentions to Yahoo Finance tickers
CRYPTO_TICKERS = {
    "BTC": "BTC-USD",
    "BITCOIN": "BTC-USD",
    "ETH": "ETH-USD",
    "ETHEREUM": "ETH-USD",
    "SOL": "SOL-USD",
    "SOLANA": "SOL-USD",
    "ADA": "ADA-USD",
    "CARDANO": "ADA-USD",
    "XRP": "XRP-USD",
    "RIPPLE": "XRP-USD",
    "DOGE": "DOGE-USD",
    "LINK": "LINK-USD",
    "CHAINLINK": "LINK-USD",
    "DOT": "DOT-USD",
    "POLKADOT": "DOT-USD",
    "AVAX": "AVAX-USD",
    "MATIC": "MATIC-USD",
    "POLYGON": "MATIC-USD",
    "UNI": "UNI-USD",
    "UNISWAP": "UNI-USD",
    "ATOM": "ATOM-USD",
    "NEAR": "NEAR-USD",
    "FTM": "FTM-USD",
    "FANTOM": "FTM-USD",
    "OP": "OP-USD",
    "OPTIMISM": "OP-USD",
    "ARB": "ARB-USD",
    "ARBITRUM": "ARB-USD",
    "APE": "APE-USD",
    "LTC": "LTC-USD",
    "LITECOIN": "LTC-USD",
    "BCH": "BCH-USD",
    "AAVE": "AAVE-USD",
    "CRV": "CRV-USD",
    "MSTR": "MSTR",  # MicroStrategy stock
    "SAYLOR": "MSTR",
    "COINBASE": "COIN",
    "COIN": "COIN",
    "MARA": "MARA",
    "RIOT": "RIOT",
    "SUI": "SUI20947-USD",
    "TIA": "TIA22861-USD",
    "SEI": "SEI-USD",
    "INJ": "INJ-USD",
    "INJECTIVE": "INJ-USD",
    "PEPE": "PEPE24478-USD",
    "WIF": "WIF-USD",
    "BONK": "BONK-USD",
    "JUP": "JUP29210-USD",
    "RENDER": "RENDER-USD",
    "RNDR": "RENDER-USD",
    "FET": "FET-USD",
    "TAO": "TAO22974-USD",
    "RUNE": "RUNE-USD",
    "THORCHAIN": "RUNE-USD",
    "MKR": "MKR-USD",
    "COMP": "COMP-USD",
    "SNX": "SNX-USD",
    "PENDLE": "PENDLE-USD",
    "STX": "STX-USD",
    "STACKS": "STX-USD",
    "HBAR": "HBAR-USD",
    "HEDERA": "HBAR-USD",
    "APT": "APT21794-USD",
    "APTOS": "APT21794-USD",
    "FIL": "FIL-USD",
    "ICP": "ICP-USD",
    "TRX": "TRX-USD",
    "TRON": "TRX-USD",
    "VET": "VET-USD",
    "ALGO": "ALGO-USD",
    "LUNA": "LUNA-USD",
    "LUNC": "LUNC-USD",
    "TERRA": "LUNA-USD",
    "FTT": "FTT-USD",
    "BNB": "BNB-USD",
    "SHIB": "SHIB-USD",
    "MON": None,  # Monad - not tradeable on standard exchanges yet
    "MONAD": None,
    "KAITO": None,
    "BERA": None,
    "BERACHAIN": None,
}

# ── Signal extraction patterns ──────────────────────────────────────────────

# Keywords that indicate a directional position
BULLISH_KEYWORDS = [
    r'\bbuy\b', r'\bbought\b', r'\bbuying\b', r'\blong\b', r'\blonged\b',
    r'\bbullish\b', r'\bbull\b', r'\baccumulate\b', r'\baccumulating\b',
    r'\bbid\b', r'\bbidding\b', r'\bentry\b', r'\bentered\b',
    r'\bflipping bullish\b', r'\bleaning bullish\b',
    r'\bgoing long\b', r'\bwent long\b',
    r'\bsupport\b.*\bbounce\b', r'\bdip.?buy\b',
    r'\breclaim\b', r'\bbreakout\b',
    r'\bup\s+from\s+here\b', r'\bhigher\b.*\bfrom\b',
]

BEARISH_KEYWORDS = [
    r'\bsell\b', r'\bsold\b', r'\bselling\b', r'\bshort\b', r'\bshorting\b',
    r'\bshorted\b', r'\bbearish\b', r'\bbear\b',
    r'\bdump\b', r'\bdumped\b', r'\bdumping\b',
    r'\bflipping bearish\b', r'\bleaning bearish\b',
    r'\bclosed\b.*\bposition\b', r'\bexit\b', r'\bexited\b',
    r'\bgoing short\b', r'\bwent short\b',
    r'\bbreakdown\b', r'\bfailed\b.*\bsupport\b',
    r'\bovervalued\b', r'\btop\b.*\bin\b',
]

NEUTRAL_EXIT_KEYWORDS = [
    r'\bclosed\b.*\bposition', r'\bflat\b', r'\bsidelined\b',
    r'\bcash\b', r'\bout\b.*\bposition',
]

# Price level patterns
PRICE_PATTERN = re.compile(
    r'\$\s?([\d,]+\.?\d*)\s*k?\b'  # $84k, $93.5k, $0.025
    r'|'
    r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:usd|dollars?)\b'  # 84000 usd
    r'|'
    r'(?:at|from|to|above|below|near|around|price|level)\s+\$?\s?([\d,]+\.?\d*)\s*k?\b',  # at 84k
    re.IGNORECASE
)


def load_tweets(path: Path) -> list[dict]:
    """Load tweets from JSONL file."""
    tweets = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                tweets.append(json.loads(line))
    return tweets


def extract_mentioned_tokens(tweet: dict) -> list[str]:
    """Extract crypto tokens mentioned in a tweet."""
    tokens = set()

    # Use pre-extracted tickers if available
    if tweet.get("mentioned_tickers"):
        for t in tweet["mentioned_tickers"]:
            t_upper = t.upper()
            if t_upper in CRYPTO_TICKERS:
                tokens.add(t_upper)

    # Also scan text for $ mentions
    text = tweet.get("text", "")
    for match in re.finditer(r'\$([A-Za-z]+)', text):
        symbol = match.group(1).upper()
        if symbol in CRYPTO_TICKERS:
            tokens.add(symbol)

    # Scan for token names in text
    text_upper = text.upper()
    for name in ["BITCOIN", "ETHEREUM", "SOLANA", "CARDANO"]:
        if name in text_upper:
            tokens.add(name)

    return list(tokens)


def classify_signal(text: str) -> tuple[str | None, float]:
    """Classify tweet direction and confidence.
    Returns (direction, confidence) where direction is 'bull', 'bear', 'exit', or None.
    """
    text_lower = text.lower()
    bull_score = 0
    bear_score = 0
    exit_score = 0

    for pattern in BULLISH_KEYWORDS:
        if re.search(pattern, text_lower):
            bull_score += 1

    for pattern in BEARISH_KEYWORDS:
        if re.search(pattern, text_lower):
            bear_score += 1

    for pattern in NEUTRAL_EXIT_KEYWORDS:
        if re.search(pattern, text_lower):
            exit_score += 1

    total = bull_score + bear_score + exit_score
    if total == 0:
        return None, 0.0

    if exit_score > 0 and exit_score >= bull_score and exit_score >= bear_score:
        return "exit", exit_score / total

    if bull_score > bear_score:
        return "bull", bull_score / total
    elif bear_score > bull_score:
        return "bear", bear_score / total
    else:
        # Mixed signals
        return None, 0.0


def extract_price_levels(text: str) -> list[float]:
    """Extract price levels mentioned in text."""
    prices = []
    # Handle $Xk format
    for match in re.finditer(r'\$\s?([\d,]+\.?\d*)\s*k\b', text, re.IGNORECASE):
        try:
            val = float(match.group(1).replace(',', '')) * 1000
            prices.append(val)
        except ValueError:
            pass

    # Handle plain $ amounts
    for match in re.finditer(r'\$\s?([\d,]+\.?\d+)\b(?!\s*k)', text, re.IGNORECASE):
        try:
            val = float(match.group(1).replace(',', ''))
            if val > 0:
                prices.append(val)
        except ValueError:
            pass

    return prices


def is_signal_tweet(tweet: dict) -> bool:
    """Determine if a tweet contains a potential trading signal."""
    # Skip retweets
    if tweet.get("is_retweet"):
        return False

    text = tweet.get("text", "")
    if not text:
        return False

    # Must mention at least one crypto token
    tokens = extract_mentioned_tokens(tweet)
    if not tokens:
        # Also check for generic crypto terms with direction
        text_lower = text.lower()
        has_crypto_context = any(term in text_lower for term in [
            "bitcoin", "crypto", "btc", "eth", "altcoin", "alt", "coin",
        ])
        if not has_crypto_context:
            return False

    # Must have directional language
    direction, confidence = classify_signal(text)
    if direction is None:
        return False

    return True


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
            matching = [d.date() for d in hist.index]
        closest = max(matching) if matching else min(d.date() for d in hist.index)
        row = hist.loc[hist.index.date == closest]
        if row.empty:
            return None
        return float(row["Close"].iloc[0])
    except Exception as e:
        return None


def fetch_current_price(ticker: str) -> tuple[float | None, str | None]:
    """Fetch current/latest price for ticker."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if hist.empty:
            return None, None
        price = float(hist["Close"].iloc[-1])
        date_str = hist.index[-1].strftime("%Y-%m-%d")
        return price, date_str
    except Exception:
        return None, None


def fetch_price_after_days(ticker: str, base_date: datetime, days: int) -> float | None:
    """Fetch price N days after base_date."""
    target = base_date + timedelta(days=days)
    if target > datetime.now():
        return None
    return fetch_price_at_date(ticker, target)


def calc_return(entry: float | None, exit_: float | None, direction: str = "bull") -> float | None:
    """Calculate percentage return, accounting for direction."""
    if entry is None or exit_ is None or entry == 0:
        return None
    ret = ((exit_ - entry) / entry) * 100
    if direction == "bear":
        ret = -ret  # Shorts profit when price goes down
    return ret


# ── Phase 1: Extract and classify all signal tweets ────────────────────────

def phase1_extract_signals():
    """Extract all potential trading signal tweets."""
    tweet_path = PROJECT_ROOT / "data" / "twitter" / "raw" / "cryptodonalt" / "tweets.jsonl"
    tweets = load_tweets(tweet_path)

    print(f"Loaded {len(tweets):,} tweets")
    print(f"Date range: {tweets[-1].get('posted_at', 'N/A')[:10]} to {tweets[0].get('posted_at', 'N/A')[:10]}")
    print()

    # Sort by date ascending
    tweets.sort(key=lambda t: t.get("posted_at", ""))

    signals = []
    token_counts = Counter()
    direction_counts = Counter()
    yearly_counts = Counter()

    for tweet in tweets:
        if not is_signal_tweet(tweet):
            continue

        text = tweet.get("text", "")
        tokens = extract_mentioned_tokens(tweet)
        direction, confidence = classify_signal(text)
        prices = extract_price_levels(text)
        date_str = tweet.get("posted_at", "")[:10]
        year = date_str[:4]

        # If no specific tokens found, try to infer from context
        if not tokens:
            text_lower = text.lower()
            if "bitcoin" in text_lower or "btc" in text_lower:
                tokens = ["BTC"]
            elif "eth" in text_lower or "ethereum" in text_lower:
                tokens = ["ETH"]

        signal = {
            "date": date_str,
            "tweet_id": tweet.get("id", ""),
            "text": text,
            "tokens": tokens,
            "direction": direction,
            "confidence": confidence,
            "price_levels": prices,
            "is_reply": tweet.get("is_reply", False),
            "is_quote": tweet.get("is_quote", False),
            "likes": tweet.get("likes", 0),
            "views": tweet.get("views", 0),
        }
        signals.append(signal)

        for token in tokens:
            token_counts[token] += 1
        direction_counts[direction] += 1
        yearly_counts[year] += 1

    print(f"Found {len(signals)} potential signal tweets")
    print()
    print("Signals by year:")
    for year in sorted(yearly_counts.keys()):
        print(f"  {year}: {yearly_counts[year]}")
    print()
    print("Top tokens mentioned in signals:")
    for token, count in token_counts.most_common(20):
        print(f"  {token}: {count}")
    print()
    print(f"Direction breakdown: {dict(direction_counts)}")

    return signals


# ── Phase 2: Deduplicate and extract key calls ──────────────────────────────

def phase2_extract_key_calls(signals: list[dict]) -> list[dict]:
    """Extract the most important, clear trading calls.

    Strategy: For each token, find distinct "position changes" where DonAlt
    clearly shifts from bull to bear or vice versa, or enters/exits.
    Focus on high-engagement tweets (more likes = more conviction/visibility).
    """
    # Focus on original tweets (not replies) with clear single-token focus
    key_calls = []
    seen_positions = {}  # (token, direction, month) -> best tweet

    for signal in signals:
        # Prefer non-reply tweets with high engagement
        if signal["is_reply"] and signal["likes"] < 100:
            continue

        tokens = signal["tokens"]
        if not tokens:
            continue

        direction = signal["direction"]
        if direction == "exit":
            continue  # We'll handle exits separately

        date_str = signal["date"]
        month_key = date_str[:7]  # YYYY-MM

        for token in tokens:
            key = (token, direction, month_key)
            if key not in seen_positions or signal["likes"] > seen_positions[key]["likes"]:
                seen_positions[key] = signal

    # Sort by date
    key_calls = sorted(seen_positions.values(), key=lambda s: s["date"])

    print(f"\nExtracted {len(key_calls)} distinct position signals")
    return key_calls


# ── Phase 3: Fetch prices and calculate performance ─────────────────────────

def phase3_calculate_performance(calls: list[dict]) -> list[dict]:
    """Fetch prices and calculate returns for each call."""
    results = []
    total = len(calls)

    for i, call in enumerate(calls):
        tokens = call["tokens"]
        if not tokens:
            continue

        # Use the primary (first) token
        primary_token = tokens[0]
        yahoo_ticker = CRYPTO_TICKERS.get(primary_token)

        if yahoo_ticker is None:
            # Token not tradeable on Yahoo Finance
            continue

        direction = call["direction"]
        date_str = call["date"]
        tweet_date = datetime.strptime(date_str, "%Y-%m-%d")

        print(f"[{i+1}/{total}] {primary_token} ({direction}) {date_str} - {call['text'][:60]}...")

        time.sleep(0.5)
        entry_price = fetch_price_at_date(yahoo_ticker, tweet_date)
        if entry_price is None:
            print(f"  -> SKIP: No entry price for {yahoo_ticker}")
            continue

        time.sleep(0.4)
        price_1w = fetch_price_after_days(yahoo_ticker, tweet_date, 7)
        time.sleep(0.3)
        price_1m = fetch_price_after_days(yahoo_ticker, tweet_date, 30)
        time.sleep(0.3)
        price_3m = fetch_price_after_days(yahoo_ticker, tweet_date, 90)
        time.sleep(0.3)
        price_6m = fetch_price_after_days(yahoo_ticker, tweet_date, 180)
        time.sleep(0.3)
        current_price, current_date = fetch_current_price(yahoo_ticker)

        result = {
            "date": date_str,
            "token": primary_token,
            "yahoo_ticker": yahoo_ticker,
            "direction": direction,
            "tweet_id": call["tweet_id"],
            "text": call["text"][:200],
            "likes": call["likes"],
            "views": call.get("views", 0),
            "price_levels_mentioned": call["price_levels"],
            "entry_price": entry_price,
            "price_1w": price_1w,
            "price_1m": price_1m,
            "price_3m": price_3m,
            "price_6m": price_6m,
            "current_price": current_price,
            "current_date": current_date,
            "return_1w": calc_return(entry_price, price_1w, direction),
            "return_1m": calc_return(entry_price, price_1m, direction),
            "return_3m": calc_return(entry_price, price_3m, direction),
            "return_6m": calc_return(entry_price, price_6m, direction),
            "return_current": calc_return(entry_price, current_price, direction),
        }
        results.append(result)

        ret_str = f"1w:{result['return_1w']:+.1f}%" if result["return_1w"] is not None else "1w:N/A"
        ret_str += f"  1m:{result['return_1m']:+.1f}%" if result["return_1m"] is not None else "  1m:N/A"
        ret_str += f"  3m:{result['return_3m']:+.1f}%" if result["return_3m"] is not None else "  3m:N/A"
        print(f"  Entry: ${entry_price:,.2f} | {ret_str}")

    return results


def print_summary(results: list[dict]):
    """Print aggregate statistics."""
    print()
    print("=" * 100)
    print("AGGREGATE STATISTICS - @CryptoDonAlt Trading Calls")
    print("=" * 100)

    # Overall stats
    for interval_name, key in [("1 Week", "return_1w"), ("1 Month", "return_1m"),
                                ("3 Months", "return_3m"), ("6 Months", "return_6m"),
                                ("Current", "return_current")]:
        returns = [r[key] for r in results if r.get(key) is not None]
        if not returns:
            continue
        winners = [r for r in returns if r > 0]
        avg = sum(returns) / len(returns)
        median = sorted(returns)[len(returns) // 2]
        best = max(returns)
        worst = min(returns)
        win_rate = len(winners) / len(returns) * 100

        print(f"\n{interval_name} ({len(returns)} calls with data):")
        print(f"  Win Rate:    {win_rate:.0f}% ({len(winners)}/{len(returns)})")
        print(f"  Avg Return:  {avg:+.1f}%")
        print(f"  Median:      {median:+.1f}%")
        print(f"  Best:        {best:+.1f}%")
        print(f"  Worst:       {worst:+.1f}%")

    # By direction
    for direction in ["bull", "bear"]:
        dir_results = [r for r in results if r["direction"] == direction]
        if not dir_results:
            continue
        print(f"\n{'─' * 50}")
        print(f"  {direction.upper()} CALLS ONLY ({len(dir_results)} calls):")
        for interval_name, key in [("1W", "return_1w"), ("1M", "return_1m"), ("3M", "return_3m")]:
            returns = [r[key] for r in dir_results if r.get(key) is not None]
            if not returns:
                continue
            winners = [r for r in returns if r > 0]
            avg = sum(returns) / len(returns)
            win_rate = len(winners) / len(returns) * 100
            print(f"    {interval_name}: WR {win_rate:.0f}% | Avg {avg:+.1f}% | n={len(returns)}")

    # By year
    print(f"\n{'─' * 50}")
    print("  BY YEAR:")
    yearly = defaultdict(list)
    for r in results:
        year = r["date"][:4]
        if r.get("return_3m") is not None:
            yearly[year].append(r["return_3m"])
    for year in sorted(yearly.keys()):
        rets = yearly[year]
        avg = sum(rets) / len(rets)
        winners = [r for r in rets if r > 0]
        wr = len(winners) / len(rets) * 100
        print(f"    {year}: {len(rets)} calls | 3M Avg: {avg:+.1f}% | WR: {wr:.0f}%")

    # By token
    print(f"\n{'─' * 50}")
    print("  BY TOKEN (3M returns):")
    token_rets = defaultdict(list)
    for r in results:
        if r.get("return_3m") is not None:
            token_rets[r["token"]].append(r["return_3m"])
    for token, rets in sorted(token_rets.items(), key=lambda x: -len(x[1])):
        if len(rets) < 2:
            continue
        avg = sum(rets) / len(rets)
        winners = [r for r in rets if r > 0]
        wr = len(winners) / len(rets) * 100
        print(f"    {token}: {len(rets)} calls | Avg: {avg:+.1f}% | WR: {wr:.0f}%")


def print_results_table(results: list[dict]):
    """Print results as a table."""
    print()
    print("=" * 100)
    print("RESULTS TABLE")
    print("=" * 100)
    print()

    header = f"{'Date':<12} {'Token':<8} {'Dir':<5} {'Entry':>10} {'1W':>8} {'1M':>8} {'3M':>8} {'6M':>8} {'Now':>8} {'Likes':>6}"
    print(header)
    print("-" * len(header))

    for r in results:
        def fmt_ret(v):
            return f"{v:+.1f}%" if v is not None else "N/A"

        print(
            f"{r['date']:<12} {r['token']:<8} {r['direction']:<5} "
            f"${r['entry_price']:>9,.2f} "
            f"{fmt_ret(r.get('return_1w')):>8} {fmt_ret(r.get('return_1m')):>8} "
            f"{fmt_ret(r.get('return_3m')):>8} {fmt_ret(r.get('return_6m')):>8} "
            f"{fmt_ret(r.get('return_current')):>8} {r.get('likes', 0):>6}"
        )


def main():
    print("=" * 100)
    print("FACT-CHECK: @CryptoDonAlt Twitter Trading Calls")
    print("=" * 100)
    print()

    # Phase 1: Extract all signal tweets
    print("PHASE 1: Extracting signal tweets...")
    print("-" * 50)
    signals = phase1_extract_signals()

    # Phase 2: Deduplicate to key calls
    print()
    print("PHASE 2: Extracting key position changes...")
    print("-" * 50)
    key_calls = phase2_extract_key_calls(signals)

    # Save extracted signals for review
    signals_path = PROJECT_ROOT / "data" / "twitter" / "analyses" / "cryptodonalt_signals.json"
    signals_path.parent.mkdir(parents=True, exist_ok=True)
    with open(signals_path, "w") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total_tweets": 11614,
            "signal_tweets": len(signals),
            "key_calls": len(key_calls),
            "signals": [
                {
                    "date": s["date"],
                    "tokens": s["tokens"],
                    "direction": s["direction"],
                    "confidence": s["confidence"],
                    "likes": s["likes"],
                    "text": s["text"][:300],
                    "tweet_id": s["tweet_id"],
                }
                for s in key_calls
            ],
        }, f, indent=2, ensure_ascii=False)
    print(f"\nSignals saved to {signals_path}")

    # Phase 3: Fetch prices
    print()
    print("PHASE 3: Fetching prices and calculating performance...")
    print("-" * 50)
    results = phase3_calculate_performance(key_calls)

    # Print results
    print_results_table(results)
    print_summary(results)

    # Save results
    output_path = PROJECT_ROOT / "data" / "twitter" / "analyses" / "cryptodonalt_factcheck.json"
    with open(output_path, "w") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total_tweets_analyzed": 11614,
            "signal_tweets_found": len(signals),
            "key_calls_evaluated": len(key_calls),
            "results_with_prices": len(results),
            "results": results,
        }, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
