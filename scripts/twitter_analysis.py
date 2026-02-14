#!/usr/bin/env python3
"""
Comprehensive Twitter/X Investment Account Analysis
Analyzes 16 accounts for signal quality, investment focus, and engagement metrics.
"""

import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

DATA_DIR = Path("/Users/pontus/Developer/finance-agent/data/twitter/raw")

HANDLES = [
    "abcampbell", "abcpokerbi", "alexeliasson", "cryptodonalt",
    "james56487175", "jave_t23", "matematikern3", "melmattison1",
    "mrmikeinvesting", "nolimitgains", "originalbraila", "pakpakchicken",
    "palma_fire", "snaljapen", "venturafpc", "vildkatten"
]

# --- Ticker / Asset Patterns ---

# Cashtag pattern: $TSLA, $BTC, etc.
CASHTAG_RE = re.compile(r'\$([A-Z]{2,6})\b')

# Major international tickers (case-insensitive matching in text)
INTL_TICKERS = [
    "TSLA", "AAPL", "MSFT", "NVDA", "AMZN", "GOOG", "GOOGL", "META",
    "AMD", "INTC", "NFLX", "DIS", "BA", "JPM", "GS", "MS",
    "SPY", "QQQ", "IWM", "VIX", "SPX", "NDX",
    "PLTR", "SOFI", "RIVN", "LCID", "NIO", "COIN", "MSTR",
    "GME", "AMC", "BBBY", "DWAC",
]

# Swedish tickers and company names (common on Swedish FinTwit)
SWEDISH_TICKERS = [
    "Volvo", "Ericsson", "SBB", "Saab", "Hexagon", "Sandvik", "Atlas Copco",
    "ABB", "AstraZeneca", "Investor", "Kinnevik", "Telia", "Sinch",
    "H&M", "Boliden", "Lundin", "Embracer", "Paradox", "Millicom",
    "Securitas", "Electrolux", "Alfa Laval", "Getinge", "Nibe",
    "Castellum", "Fastighets", "Balder", "Samhällsbygg", "NP3",
    "Sagax", "Corem", "Fabege", "Wihlborgs", "Hufvudstaden",
    "Evolution", "EVO", "Nordnet", "Avanza", "SEB", "Handelsbanken",
    "Swedbank", "Skanska", "Peab", "NCC", "JM",
    "Essity", "SCA", "Stora Enso", "BillerudKorsnäs",
    "Addnode", "Fortnox", "Vitec", "Lime", "Readly",
    "Storytel", "Stillfront", "Modern Times", "MTG",
    "OMXS30", "OMX", "Stockholmsbörsen",
    "LMK Group", "Rheinmetall", "BAE Systems",
    "Arise", "OX2", "Climeon",
]

# Crypto assets
CRYPTO_ASSETS = [
    "BTC", "Bitcoin", "ETH", "Ethereum", "SOL", "Solana",
    "XRP", "ADA", "Cardano", "DOGE", "Dogecoin", "SHIB",
    "AVAX", "DOT", "Polkadot", "MATIC", "Polygon", "LINK",
    "Chainlink", "UNI", "Uniswap", "AAVE", "LTC", "Litecoin",
    "BNB", "PEPE", "BONK", "WIF", "JUP", "ARB", "OP",
    "SUI", "APT", "SEI", "TIA", "INJ", "NEAR", "FTM",
    "HBAR", "ALGO", "ATOM", "ICP", "FIL", "RNDR", "GRT",
    "altcoin", "altcoins", "DeFi", "NFT", "memecoin",
]

# Commodities
COMMODITIES = [
    "guld", "gold", "silver", "oil", "olja", "koppar", "copper",
    "uran", "uranium", "palladium", "platinum", "nickel",
    "natural gas", "naturgas", "wheat", "corn",
]

# Macro terms
MACRO_TERMS = [
    "ränta", "räntor", "inflation", "deflation", "recession",
    "fed", "riksbank", "ecb", "centralbank",
    "BNP", "GDP", "CPI", "PMI", "arbetsmarknad", "unemployment",
    "yield", "bond", "obligation", "dollar", "euro", "krona",
    "DXY", "treasury", "treasuries",
    "makro", "macro", "bull market", "bear market",
    "QE", "QT", "rate cut", "rate hike", "räntesänk", "räntehöj",
]

# --- Actionable Investment Language ---
ACTIONABLE_PATTERNS_EN = [
    r'\bbuy\b', r'\bsell\b', r'\blong\b', r'\bshort\b',
    r'\bbullish\b', r'\bbearish\b',
    r'\btarget\b', r'\bprice target\b',
    r'\bentry\b', r'\bexit\b',
    r'\bstop.?loss\b', r'\btake.?profit\b',
    r'\bbreakout\b', r'\bbreakdown\b',
    r'\bsupport\b', r'\bresistance\b',
    r'\baccumulate\b', r'\bdistribut\b',
    r'\boverweight\b', r'\bunderweight\b',
    r'\bhold\b', r'\badd\b',
    r'\bdip\s*buy\b', r'\bbuying\s*the\s*dip\b',
    r'\bgoing\s+long\b', r'\bgoing\s+short\b',
    r'\bTP\d*\b', r'\bSL\b',
    r'\bR:R\b', r'\brisk.?reward\b',
    r'\bleverag', r'\bmargin\b',
]

ACTIONABLE_PATTERNS_SV = [
    r'\bköp\b', r'\bsälj\b', r'\bkort\b', r'\blång\b',
    r'\briktkurs\b', r'\bkursmål\b',
    r'\bstöd\b', r'\bmotstånd\b',
    r'\bhausse\b', r'\bbaisse\b',
    r'\btillväxt\b', r'\bvärdering\b',
    r'\bP/?E\b', r'\bEV/?EBITDA\b', r'\bEV/?S\b',
    r'\bplockar\s+in\b', r'\bsålt\b', r'\bköpt\b',
    r'\bökar\b', r'\bminskar\b',
    r'\bportfölj\b', r'\binnehav\b',
    r'\butdelning\b', r'\bdirektavkastning\b',
    r'\brapport\b', r'\bkvartalsrapport\b',
    r'\brekommendat\b',
]

ALL_ACTIONABLE = [re.compile(p, re.IGNORECASE) for p in ACTIONABLE_PATTERNS_EN + ACTIONABLE_PATTERNS_SV]

# Price target patterns (specific numbers)
PRICE_TARGET_RE = re.compile(
    r'(?:target|riktkurs|kursmål|price\s*target|PT|TP)\s*[:=@]?\s*\$?\d+[\.,]?\d*'
    r'|'
    r'\$?\d+[\.,]?\d*\s*(?:target|riktkurs|kursmål)'
    r'|'
    r'(?:riktkurs|kursmål|target)\s+(?:på|at|of|around)\s+\$?\d+[\.,]?\d*'
    r'|'
    r'(?:köp|buy)\s+(?:under|below|at)\s+\$?\d+[\.,]?\d*'
    r'|'
    r'(?:sälj|sell)\s+(?:över|above|at)\s+\$?\d+[\.,]?\d*',
    re.IGNORECASE
)

# Numeric prediction patterns (X will go to Y, etc.)
NUMERIC_PREDICTION_RE = re.compile(
    r'(?:will|going|headed|ska|kommer)\s+(?:to|till|mot)\s+\$?\d+'
    r'|'
    r'(?:see|ser|expect|förvänta)\s+\$?\d+'
    r'|'
    r'\b\d+k?\s*(?:incoming|next|soon|snart)',
    re.IGNORECASE
)

# Self-promotion / engagement bait patterns
SELF_PROMO_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r'follow\s+(?:me|us|for)',
        r'(?:like|retweet|RT)\s+(?:if|this)',
        r'giveaway',
        r'DM\s+(?:me|for)',
        r'subscribe',
        r'check\s+(?:out|my)\s+(?:link|bio|channel|youtube|podcast)',
        r'link\s+in\s+bio',
        r'free\s+(?:course|guide|ebook|webinar|signal)',
        r'join\s+(?:my|our|the)\s+(?:group|channel|discord|telegram|community)',
        r'promo\s*code',
        r'use\s+(?:my|code)',
        r'referral',
        r'affiliate',
        r'paid\s+group',
        r'VIP\s+(?:group|access|signal)',
    ]
]


# ============================================================
# ANALYSIS FUNCTIONS
# ============================================================

def load_tweets(handle: str) -> list[dict]:
    """Load all tweets for a handle from JSONL file."""
    path = DATA_DIR / handle / "tweets.jsonl"
    tweets = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tweets.append(json.loads(line))
    return tweets


def find_tickers_in_text(text: str) -> dict:
    """Find mentioned tickers/assets in text. Returns dict of categories."""
    found = {"cashtags": [], "intl_stocks": [], "swedish": [], "crypto": [], "commodities": []}
    text_upper = text.upper()
    text_lower = text.lower()

    # Cashtags
    cashtags = CASHTAG_RE.findall(text)
    found["cashtags"] = cashtags

    # International stocks (only if mentioned as standalone words)
    for t in INTL_TICKERS:
        if re.search(r'\b' + re.escape(t) + r'\b', text_upper):
            found["intl_stocks"].append(t)

    # Swedish tickers/companies
    for t in SWEDISH_TICKERS:
        if re.search(r'\b' + re.escape(t.lower()) + r'\b', text_lower):
            found["swedish"].append(t)

    # Crypto
    for t in CRYPTO_ASSETS:
        if re.search(r'\b' + re.escape(t.lower()) + r'\b', text_lower):
            found["crypto"].append(t)

    # Commodities
    for t in COMMODITIES:
        if re.search(r'\b' + re.escape(t.lower()) + r'\b', text_lower):
            found["commodities"].append(t)

    return found


def has_actionable_language(text: str) -> bool:
    """Check if text contains actionable investment language."""
    for pat in ALL_ACTIONABLE:
        if pat.search(text):
            return True
    return False


def has_price_target(text: str) -> bool:
    """Check if text contains specific price targets."""
    return bool(PRICE_TARGET_RE.search(text) or NUMERIC_PREDICTION_RE.search(text))


def is_self_promo(text: str) -> bool:
    """Check if tweet is self-promotional or engagement bait."""
    for pat in SELF_PROMO_PATTERNS:
        if pat.search(text):
            return True
    return False


def classify_investment_focus(ticker_counts: dict) -> str:
    """Classify the investment focus of an account."""
    scores = {
        "Stocks (International)": ticker_counts.get("intl_stocks", 0),
        "Stocks (Swedish)": ticker_counts.get("swedish", 0),
        "Crypto": ticker_counts.get("crypto", 0),
        "Commodities": ticker_counts.get("commodities", 0),
    }

    # Check for macro focus separately
    macro_score = ticker_counts.get("macro", 0)
    scores["Macro/Economics"] = macro_score

    if all(v == 0 for v in scores.values()):
        return "Unclear / General"

    # Sort by score
    sorted_scores = sorted(scores.items(), key=lambda x: -x[1])

    # If top 2 are close, list both
    top = sorted_scores[0]
    second = sorted_scores[1]

    if second[1] > 0 and second[1] >= top[1] * 0.4:
        return f"{top[0]} + {second[0]}"
    elif top[1] > 0:
        return top[0]
    else:
        return "Unclear / General"


def analyze_handle(handle: str) -> dict:
    """Run full analysis on a single handle."""
    tweets = load_tweets(handle)

    if not tweets:
        return {"handle": handle, "error": "No tweets found"}

    # --- Basic Stats ---
    total = len(tweets)
    dates = []
    for t in tweets:
        try:
            dates.append(datetime.fromisoformat(t["posted_at"].replace("Z", "+00:00")))
        except:
            pass

    date_range = ""
    if dates:
        earliest = min(dates)
        latest = max(dates)
        date_range = f"{earliest.strftime('%Y-%m-%d')} to {latest.strftime('%Y-%m-%d')}"
        days_span = (latest - earliest).days or 1
    else:
        days_span = 1

    likes = [t.get("likes", 0) or 0 for t in tweets]
    views = [t.get("views", 0) or 0 for t in tweets]
    retweets_count = [t.get("retweets", 0) or 0 for t in tweets]
    replies_count = [t.get("replies", 0) or 0 for t in tweets]

    avg_likes = sum(likes) / total
    avg_views = sum(views) / total if any(v > 0 for v in views) else 0
    avg_retweets = sum(retweets_count) / total
    median_likes = sorted(likes)[total // 2]
    median_views = sorted(views)[total // 2]

    # Engagement rate (likes+retweets / views)
    total_engagement = sum(likes) + sum(retweets_count)
    total_views = sum(views)
    engagement_rate = (total_engagement / total_views * 100) if total_views > 0 else 0

    # --- Tweet Type Breakdown ---
    original_tweets = [t for t in tweets if not t.get("is_reply") and not t.get("is_retweet") and not t.get("is_quote")]
    reply_tweets = [t for t in tweets if t.get("is_reply")]
    quote_tweets = [t for t in tweets if t.get("is_quote")]
    retweet_tweets = [t for t in tweets if t.get("is_retweet")]

    # --- Signal Analysis ---
    ticker_tweets = 0
    actionable_tweets = 0
    price_target_tweets = 0
    self_promo_tweets = 0
    macro_tweets = 0

    all_cashtags = Counter()
    all_intl = Counter()
    all_swedish = Counter()
    all_crypto = Counter()
    all_commodities = Counter()

    ticker_category_counts = defaultdict(int)  # for focus classification

    investment_content_tweets = 0  # tweets with ANY investment signal

    sample_signal_tweets = []  # store examples of high-signal tweets

    for t in tweets:
        text = t.get("text", "")

        # Ticker detection
        tickers = find_tickers_in_text(text)
        has_ticker = False

        for tag in tickers["cashtags"]:
            all_cashtags[tag] += 1
            has_ticker = True
        for tag in tickers["intl_stocks"]:
            all_intl[tag] += 1
            has_ticker = True
        for tag in tickers["swedish"]:
            all_swedish[tag] += 1
            has_ticker = True
        for tag in tickers["crypto"]:
            all_crypto[tag] += 1
            has_ticker = True
        for tag in tickers["commodities"]:
            all_commodities[tag] += 1
            has_ticker = True

        # Also use pre-extracted mentioned_tickers field
        if t.get("mentioned_tickers"):
            has_ticker = True
            for mt in t["mentioned_tickers"]:
                all_cashtags[mt] += 1

        if has_ticker:
            ticker_tweets += 1

        # Actionable language
        has_action = has_actionable_language(text)
        if has_action:
            actionable_tweets += 1

        # Price targets
        has_pt = has_price_target(text)
        if has_pt:
            price_target_tweets += 1

        # Macro
        text_lower = text.lower()
        is_macro = any(re.search(r'\b' + re.escape(term.lower()) + r'\b', text_lower) for term in MACRO_TERMS)
        if is_macro:
            macro_tweets += 1

        # Self-promo
        if is_self_promo(text):
            self_promo_tweets += 1

        # Overall investment content (has ticker OR actionable language OR macro)
        if has_ticker or has_action or is_macro or has_pt:
            investment_content_tweets += 1
            # Save high-signal examples (has ticker + actionable)
            if has_ticker and (has_action or has_pt) and len(sample_signal_tweets) < 5:
                sample_signal_tweets.append(text[:200])

    # Category counts for focus classification
    ticker_category_counts["intl_stocks"] = sum(all_intl.values())
    ticker_category_counts["swedish"] = sum(all_swedish.values())
    ticker_category_counts["crypto"] = sum(all_crypto.values())
    ticker_category_counts["commodities"] = sum(all_commodities.values())
    ticker_category_counts["macro"] = macro_tweets

    # Signal-to-noise
    signal_ratio = (investment_content_tweets / total * 100) if total > 0 else 0

    # Reply ratio (how much is replies vs original)
    reply_ratio = (len(reply_tweets) / total * 100) if total > 0 else 0
    original_ratio = (len(original_tweets) / total * 100) if total > 0 else 0

    # Specificity score: combination of ticker mentions + price targets + actionable
    # Normalized per tweet
    specificity_score = 0
    if total > 0:
        specificity_score = (
            (ticker_tweets / total) * 40 +     # 40% weight: mentions specific tickers
            (actionable_tweets / total) * 30 +  # 30% weight: actionable language
            (price_target_tweets / total) * 30   # 30% weight: specific price targets
        ) * 100

    # Top tickers
    top_cashtags = all_cashtags.most_common(10)
    top_swedish = all_swedish.most_common(10)
    top_crypto = all_crypto.most_common(10)
    top_intl = all_intl.most_common(10)

    focus = classify_investment_focus(ticker_category_counts)

    # Composite signal quality score (0-100)
    # Weights: signal ratio (30%), specificity (25%), original content ratio (20%),
    #          engagement rate (15%), low self-promo (10%)
    self_promo_ratio = (self_promo_tweets / total * 100) if total > 0 else 0

    signal_quality = (
        min(signal_ratio, 100) * 0.30 +
        min(specificity_score, 100) * 0.25 +
        min(original_ratio, 100) * 0.20 +
        min(engagement_rate * 10, 100) * 0.15 +  # scale engagement rate
        max(0, 100 - self_promo_ratio * 10) * 0.10  # penalize self-promo
    )

    return {
        "handle": handle,
        "display_name": tweets[0].get("author_display_name", handle) if tweets else handle,
        "total_tweets": total,
        "date_range": date_range,
        "days_span": days_span,
        "tweets_per_day": round(total / days_span, 1),
        # Engagement
        "avg_likes": round(avg_likes, 1),
        "median_likes": median_likes,
        "avg_views": round(avg_views, 0),
        "median_views": median_views,
        "avg_retweets": round(avg_retweets, 1),
        "engagement_rate": round(engagement_rate, 2),
        # Tweet types
        "original_tweets": len(original_tweets),
        "original_pct": round(original_ratio, 1),
        "reply_tweets": len(reply_tweets),
        "reply_pct": round(reply_ratio, 1),
        "quote_tweets": len(quote_tweets),
        "retweet_tweets": len(retweet_tweets),
        # Signal
        "ticker_tweets": ticker_tweets,
        "ticker_pct": round(ticker_tweets / total * 100, 1) if total else 0,
        "actionable_tweets": actionable_tweets,
        "actionable_pct": round(actionable_tweets / total * 100, 1) if total else 0,
        "price_target_tweets": price_target_tweets,
        "price_target_pct": round(price_target_tweets / total * 100, 1) if total else 0,
        "macro_tweets": macro_tweets,
        "investment_content_tweets": investment_content_tweets,
        "signal_ratio": round(signal_ratio, 1),
        # Specificity & Focus
        "specificity_score": round(specificity_score, 1),
        "investment_focus": focus,
        # Top tickers
        "top_cashtags": top_cashtags,
        "top_swedish": top_swedish,
        "top_crypto": top_crypto,
        "top_intl": top_intl,
        # Self-promo
        "self_promo_tweets": self_promo_tweets,
        "self_promo_pct": round(self_promo_ratio, 1),
        # Composite
        "signal_quality_score": round(signal_quality, 1),
        # Examples
        "sample_signals": sample_signal_tweets,
    }


# ============================================================
# MAIN
# ============================================================

def format_ticker_list(items, max_items=8):
    """Format a list of (ticker, count) tuples."""
    if not items:
        return "  (none)"
    return "  " + ", ".join(f"{t}({c})" for t, c in items[:max_items])


def main():
    results = []

    print("=" * 100)
    print("COMPREHENSIVE TWITTER INVESTMENT ACCOUNT ANALYSIS")
    print("=" * 100)
    print()

    for handle in HANDLES:
        try:
            r = analyze_handle(handle)
            results.append(r)
        except Exception as e:
            print(f"ERROR analyzing {handle}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Print individual reports
    for r in results:
        if "error" in r:
            print(f"\n--- {r['handle']} --- ERROR: {r['error']}")
            continue

        print(f"\n{'='*100}")
        print(f"  @{r['handle']}  ({r['display_name']})")
        print(f"{'='*100}")

        print(f"\n  BASIC STATS")
        print(f"  {'Total tweets:':<30} {r['total_tweets']:>6}")
        print(f"  {'Date range:':<30} {r['date_range']}")
        print(f"  {'Tweets/day:':<30} {r['tweets_per_day']:>6}")
        print(f"  {'Avg likes:':<30} {r['avg_likes']:>6}  (median: {r['median_likes']})")
        print(f"  {'Avg views:':<30} {r['avg_views']:>6.0f}  (median: {r['median_views']})")
        print(f"  {'Avg retweets:':<30} {r['avg_retweets']:>6}")
        print(f"  {'Engagement rate:':<30} {r['engagement_rate']:>5}%")

        print(f"\n  TWEET TYPE BREAKDOWN")
        print(f"  {'Original tweets:':<30} {r['original_tweets']:>6}  ({r['original_pct']}%)")
        print(f"  {'Replies:':<30} {r['reply_tweets']:>6}  ({r['reply_pct']}%)")
        print(f"  {'Quote tweets:':<30} {r['quote_tweets']:>6}")
        print(f"  {'Retweets:':<30} {r['retweet_tweets']:>6}")

        print(f"\n  SIGNAL ANALYSIS")
        print(f"  {'Tweets with tickers:':<30} {r['ticker_tweets']:>6}  ({r['ticker_pct']}%)")
        print(f"  {'Actionable language:':<30} {r['actionable_tweets']:>6}  ({r['actionable_pct']}%)")
        print(f"  {'Specific price targets:':<30} {r['price_target_tweets']:>6}  ({r['price_target_pct']}%)")
        print(f"  {'Macro/economics:':<30} {r['macro_tweets']:>6}")
        print(f"  {'Total investment content:':<30} {r['investment_content_tweets']:>6}  ({r['signal_ratio']}%)")
        print(f"  {'SIGNAL-TO-NOISE RATIO:':<30} {r['signal_ratio']:>5}%")

        print(f"\n  SPECIFICITY & FOCUS")
        print(f"  {'Specificity score:':<30} {r['specificity_score']:>5}/100")
        print(f"  {'Investment focus:':<30} {r['investment_focus']}")

        if r['top_cashtags']:
            print(f"  Top cashtags:        {format_ticker_list(r['top_cashtags'])}")
        if r['top_swedish']:
            print(f"  Top Swedish tickers: {format_ticker_list(r['top_swedish'])}")
        if r['top_crypto']:
            print(f"  Top crypto:          {format_ticker_list(r['top_crypto'])}")
        if r['top_intl']:
            print(f"  Top intl stocks:     {format_ticker_list(r['top_intl'])}")

        print(f"\n  SELF-PROMOTION")
        print(f"  {'Self-promo tweets:':<30} {r['self_promo_tweets']:>6}  ({r['self_promo_pct']}%)")

        print(f"\n  >>> COMPOSITE SIGNAL QUALITY SCORE: {r['signal_quality_score']:.1f}/100 <<<")

        if r['sample_signals']:
            print(f"\n  SAMPLE HIGH-SIGNAL TWEETS:")
            for i, s in enumerate(r['sample_signals'][:3], 1):
                # Truncate and clean
                clean = s.replace('\n', ' ')[:150]
                print(f"    {i}. \"{clean}...\"")

    # ============================================================
    # FINAL RANKINGS
    # ============================================================

    valid = [r for r in results if "error" not in r]

    print(f"\n\n{'#'*100}")
    print(f"  FINAL RANKINGS")
    print(f"{'#'*100}")

    # --- 1. Overall Signal Quality ---
    print(f"\n{'='*80}")
    print(f"  1. OVERALL SIGNAL QUALITY SCORE (composite)")
    print(f"{'='*80}")
    ranked = sorted(valid, key=lambda x: -x["signal_quality_score"])
    for i, r in enumerate(ranked, 1):
        bar = "█" * int(r["signal_quality_score"] / 2)
        print(f"  {i:>2}. @{r['handle']:<22} {r['signal_quality_score']:>5.1f}/100  {bar}")

    # --- 2. Signal-to-Noise Ratio ---
    print(f"\n{'='*80}")
    print(f"  2. SIGNAL-TO-NOISE RATIO (% tweets with investment content)")
    print(f"{'='*80}")
    ranked = sorted(valid, key=lambda x: -x["signal_ratio"])
    for i, r in enumerate(ranked, 1):
        bar = "█" * int(r["signal_ratio"] / 2)
        print(f"  {i:>2}. @{r['handle']:<22} {r['signal_ratio']:>5.1f}%   ({r['investment_content_tweets']}/{r['total_tweets']} tweets)  {bar}")

    # --- 3. Specificity ---
    print(f"\n{'='*80}")
    print(f"  3. SPECIFICITY SCORE (tickers + actionable + price targets)")
    print(f"{'='*80}")
    ranked = sorted(valid, key=lambda x: -x["specificity_score"])
    for i, r in enumerate(ranked, 1):
        bar = "█" * int(r["specificity_score"] / 2)
        print(f"  {i:>2}. @{r['handle']:<22} {r['specificity_score']:>5.1f}/100  {bar}")

    # --- 4. Engagement ---
    print(f"\n{'='*80}")
    print(f"  4. ENGAGEMENT (average likes)")
    print(f"{'='*80}")
    ranked = sorted(valid, key=lambda x: -x["avg_likes"])
    for i, r in enumerate(ranked, 1):
        print(f"  {i:>2}. @{r['handle']:<22} avg likes: {r['avg_likes']:>7.1f}   avg views: {r['avg_views']:>8.0f}")

    # --- 5. Original Content Ratio ---
    print(f"\n{'='*80}")
    print(f"  5. ORIGINAL CONTENT RATIO (non-reply, non-retweet)")
    print(f"{'='*80}")
    ranked = sorted(valid, key=lambda x: -x["original_pct"])
    for i, r in enumerate(ranked, 1):
        bar = "█" * int(r["original_pct"] / 2)
        print(f"  {i:>2}. @{r['handle']:<22} {r['original_pct']:>5.1f}% original  {bar}")

    # --- 6. Lowest Self-Promotion ---
    print(f"\n{'='*80}")
    print(f"  6. SELF-PROMOTION RATIO (lower is better)")
    print(f"{'='*80}")
    ranked = sorted(valid, key=lambda x: x["self_promo_pct"])
    for i, r in enumerate(ranked, 1):
        print(f"  {i:>2}. @{r['handle']:<22} {r['self_promo_pct']:>5.1f}% self-promo")

    # --- 7. Investment Focus Summary ---
    print(f"\n{'='*80}")
    print(f"  7. INVESTMENT FOCUS CATEGORIES")
    print(f"{'='*80}")
    for r in sorted(valid, key=lambda x: x["handle"]):
        print(f"  @{r['handle']:<22} {r['investment_focus']}")

    # --- 8. Price Target Frequency ---
    print(f"\n{'='*80}")
    print(f"  8. PRICE TARGET FREQUENCY (specific calls)")
    print(f"{'='*80}")
    ranked = sorted(valid, key=lambda x: -x["price_target_pct"])
    for i, r in enumerate(ranked, 1):
        print(f"  {i:>2}. @{r['handle']:<22} {r['price_target_tweets']:>4} tweets ({r['price_target_pct']}%)")

    # --- Final summary ---
    print(f"\n\n{'#'*100}")
    print(f"  EXECUTIVE SUMMARY")
    print(f"{'#'*100}")

    top3_quality = sorted(valid, key=lambda x: -x["signal_quality_score"])[:3]
    top3_signal = sorted(valid, key=lambda x: -x["signal_ratio"])[:3]
    top3_specific = sorted(valid, key=lambda x: -x["specificity_score"])[:3]

    top3_q_str = ", ".join(f"@{r['handle']}({r['signal_quality_score']:.0f})" for r in top3_quality)
    top3_s_str = ", ".join(f"@{r['handle']}({r['signal_ratio']:.0f}%)" for r in top3_signal)
    top3_sp_str = ", ".join(f"@{r['handle']}({r['specificity_score']:.0f})" for r in top3_specific)
    print(f"\n  TOP 3 by Signal Quality:   {top3_q_str}")
    print(f"  TOP 3 by Signal Ratio:     {top3_s_str}")
    print(f"  TOP 3 by Specificity:      {top3_sp_str}")

    # Best overall pick
    best = top3_quality[0]
    h = best['handle']
    sq = best['signal_quality_score']
    sr = best['signal_ratio']
    sp = best['specificity_score']
    foc = best['investment_focus']
    al = best['avg_likes']
    av = best['avg_views']
    spr = best['self_promo_pct']
    print(f"\n  BEST OVERALL: @{h}")
    print(f"    Signal Quality: {sq:.1f}/100")
    print(f"    Signal Ratio: {sr}%")
    print(f"    Specificity: {sp}/100")
    print(f"    Focus: {foc}")
    print(f"    Avg Likes: {al}, Avg Views: {av:.0f}")
    print(f"    Self-Promo: {spr}%")
    print()


if __name__ == "__main__":
    main()
