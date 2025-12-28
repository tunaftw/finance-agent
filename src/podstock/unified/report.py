"""Monthly and yearly report generator for unified signals."""

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from ..prices.clients.yahoo import YahooFinanceClient
from .models import SignalType
from .search import search_signals

logger = logging.getLogger(__name__)

# Source ID to readable name mapping
SOURCE_NAMES = {
    "kortochlang": "Kort & Lansen",
    "fillorkill": "Fill or Kill",
    "kvalitetsaktiepodden": "Kvalitetsaktiepodden",
    "kvalitetforpengarna": "Kvalitet f. Pengarna",
    "borsensfinest": "Börsens Finest",
    "avanzapodden": "Avanzapodden",
    "ettrikareliv": "Ett Rikare Liv",
    "aktiepodden": "Aktiepodden",
    "borspodden": "Börspodden",
    "veckansaffarer": "Veckans Affärer",
    "veckans_trade": "Veckans Trade",
    "analyspodden": "Analyspodden",
    "technicalroundup": "Technical Roundup",
    "cryptodonalt": "CryptoDonAlt",
}


@dataclass
class ReportEntry:
    """Single entry in the report."""

    symbol: str
    yahoo_ticker: Optional[str]
    entry_price: Optional[float]
    current_price: Optional[float]
    return_pct: Optional[float]
    currency: str
    source: str
    speaker: str
    date_str: str
    signal: SignalType


def get_source_name(signal) -> str:
    """Get readable source name from signal."""
    # Extract base source_id (remove date suffixes)
    source_id = signal.source_id.split("-")[0]
    source_type = signal.source_type.value

    if source_id in SOURCE_NAMES:
        name = SOURCE_NAMES[source_id]
    else:
        # Capitalize and replace underscores/hyphens with spaces
        name = source_id.replace("_", " ").replace("-", " ").title()

    # Add source type indicator
    if source_type == "youtube":
        return f"{name} (YT)"
    elif source_type == "twitter":
        return f"@{name}"
    return name


def generate_monthly_report(
    year: int,
    month: int,
    fetch_current_prices: bool = True,
    limit: int = 500,
) -> dict:
    """
    Generate a monthly report of signals with performance data.

    Args:
        year: Year (e.g., 2025)
        month: Month (1-12)
        fetch_current_prices: Whether to fetch current prices from Yahoo
        limit: Maximum signals to include

    Returns:
        Dict with 'bullish', 'bearish', 'neutral' lists of ReportEntry
    """
    # Calculate date range
    from_date = date(year, month, 1)
    if month == 12:
        to_date = date(year + 1, 1, 1)
    else:
        to_date = date(year, month + 1, 1)
    # Go back one day to get last day of month
    to_date = date(to_date.year, to_date.month, to_date.day - 1) if to_date.day > 1 else from_date

    # For edge case where month ends on 1st
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    to_date = date(year, month, last_day)

    # Fetch signals
    signals = search_signals(
        from_date=from_date,
        to_date=to_date,
        limit=limit,
    )

    # Initialize Yahoo client if needed
    yahoo = None
    if fetch_current_prices:
        yahoo = YahooFinanceClient(rate_limit_delay=0.2)

    # Build entries grouped by signal type
    result = {
        "bullish": [],
        "bearish": [],
        "neutral": [],
        "month": f"{year}-{month:02d}",
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "total_signals": len(signals),
    }

    # Track unique tickers to avoid duplicate price fetches
    current_prices = {}

    for s in signals:
        entry = ReportEntry(
            symbol=s.asset_symbol[:12],
            yahoo_ticker=s.yahoo_ticker,
            entry_price=s.entry_price,
            current_price=None,
            return_pct=None,
            currency=s.entry_price_currency or "",
            source=get_source_name(s),
            speaker=s.speaker_name[:20] if s.speaker_name else "-",
            date_str=s.content_date.strftime("%d %b"),
            signal=s.signal,
        )

        # Fetch current price if we have entry price
        if fetch_current_prices and entry.yahoo_ticker and entry.entry_price:
            if entry.yahoo_ticker not in current_prices:
                try:
                    snapshot = yahoo.get_current_price(entry.yahoo_ticker)
                    if snapshot:
                        current_prices[entry.yahoo_ticker] = snapshot.price
                except Exception as e:
                    logger.debug(f"Failed to fetch current price for {entry.yahoo_ticker}: {e}")

            if entry.yahoo_ticker in current_prices:
                entry.current_price = current_prices[entry.yahoo_ticker]
                entry.return_pct = ((entry.current_price - entry.entry_price) / entry.entry_price) * 100

        # Add to appropriate list
        if s.signal == SignalType.BULLISH:
            result["bullish"].append(entry)
        elif s.signal == SignalType.BEARISH:
            result["bearish"].append(entry)
        else:
            result["neutral"].append(entry)

    # Sort each list by date (most recent first)
    for key in ["bullish", "bearish", "neutral"]:
        result[key].sort(key=lambda e: e.date_str, reverse=True)

    return result


def format_report_table(entries: list[ReportEntry], signal_type: str) -> str:
    """
    Format entries as a text table.

    Args:
        entries: List of ReportEntry objects
        signal_type: 'bullish' or 'bearish' for header styling

    Returns:
        Formatted table string
    """
    if not entries:
        return "  (inga signaler)\n"

    lines = []

    # Header
    if signal_type == "bearish":
        header = f"{'Ticker':<12} {'Entry':>10} {'Idag':>10} {'Avk.':>8} {'Rätt?':>5} {'Källa':<20} {'Talare':<15} {'Datum':<8}"
    else:
        header = f"{'Ticker':<12} {'Entry':>10} {'Idag':>10} {'Avk.':>8} {'Källa':<20} {'Talare':<15} {'Datum':<8}"

    lines.append(header)
    lines.append("-" * len(header))

    for e in entries:
        # Format entry price
        if e.entry_price:
            if e.entry_price >= 1000:
                entry_str = f"{e.entry_price:,.0f} {e.currency}"
            elif e.entry_price >= 1:
                entry_str = f"{e.entry_price:.2f} {e.currency}"
            else:
                entry_str = f"{e.entry_price:.4f} {e.currency}"
        else:
            entry_str = "-"

        # Format current price
        if e.current_price:
            if e.current_price >= 1000:
                current_str = f"{e.current_price:,.0f}"
            elif e.current_price >= 1:
                current_str = f"{e.current_price:.2f}"
            else:
                current_str = f"{e.current_price:.4f}"
        else:
            current_str = "-"

        # Format return
        if e.return_pct is not None:
            if e.return_pct >= 0:
                return_str = f"+{e.return_pct:.1f}%"
            else:
                return_str = f"{e.return_pct:.1f}%"
        else:
            return_str = "-"

        # For bearish: check if prediction was correct (price went down)
        if signal_type == "bearish":
            if e.return_pct is not None:
                correct = "Y" if e.return_pct < 0 else "X"
            else:
                correct = "-"
            line = f"{e.symbol:<12} {entry_str:>10} {current_str:>10} {return_str:>8} {correct:>5} {e.source:<20} {e.speaker:<15} {e.date_str:<8}"
        else:
            line = f"{e.symbol:<12} {entry_str:>10} {current_str:>10} {return_str:>8} {e.source:<20} {e.speaker:<15} {e.date_str:<8}"

        lines.append(line)

    return "\n".join(lines) + "\n"


def format_full_report(report: dict) -> str:
    """
    Format full monthly report as text.

    Args:
        report: Output from generate_monthly_report()

    Returns:
        Full formatted report string
    """
    lines = []

    # Header
    lines.append(f"\n{'=' * 60}")
    lines.append(f"  MÅNADSRAPPORT: {report['month']}")
    lines.append(f"  Period: {report['from_date']} till {report['to_date']}")
    lines.append(f"  Totalt: {report['total_signals']} signaler")
    lines.append(f"{'=' * 60}\n")

    # Bullish section
    lines.append(f"\n[+] BULLISH ({len(report['bullish'])} st)")
    lines.append("-" * 40)
    lines.append(format_report_table(report["bullish"], "bullish"))

    # Bearish section
    lines.append(f"\n[-] BEARISH ({len(report['bearish'])} st)")
    lines.append("-" * 40)
    lines.append(format_report_table(report["bearish"], "bearish"))

    # Neutral section (optional, usually less interesting)
    if report["neutral"]:
        lines.append(f"\n[~] NEUTRAL ({len(report['neutral'])} st)")
        lines.append("-" * 40)
        lines.append(format_report_table(report["neutral"], "neutral"))

    # Summary
    lines.append("\n" + "=" * 60)

    # Calculate accuracy stats
    bullish_with_return = [e for e in report["bullish"] if e.return_pct is not None]
    bearish_with_return = [e for e in report["bearish"] if e.return_pct is not None]

    if bullish_with_return:
        bullish_wins = sum(1 for e in bullish_with_return if e.return_pct > 0)
        bullish_pct = (bullish_wins / len(bullish_with_return)) * 100
        avg_bullish = sum(e.return_pct for e in bullish_with_return) / len(bullish_with_return)
        lines.append(f"  Bullish träffar: {bullish_wins}/{len(bullish_with_return)} ({bullish_pct:.0f}%), snitt: {avg_bullish:+.1f}%")

    if bearish_with_return:
        bearish_wins = sum(1 for e in bearish_with_return if e.return_pct < 0)
        bearish_pct = (bearish_wins / len(bearish_with_return)) * 100
        avg_bearish = sum(e.return_pct for e in bearish_with_return) / len(bearish_with_return)
        lines.append(f"  Bearish träffar: {bearish_wins}/{len(bearish_with_return)} ({bearish_pct:.0f}%), snitt: {avg_bearish:+.1f}%")

    lines.append("=" * 60 + "\n")

    return "\n".join(lines)


def generate_yearly_report(
    year: int,
    fetch_current_prices: bool = True,
    limit: int = 5000,
) -> dict:
    """
    Generate a yearly report of signals with performance data.

    Args:
        year: Year (e.g., 2025)
        fetch_current_prices: Whether to fetch current prices from Yahoo
        limit: Maximum signals to include

    Returns:
        Dict with 'bullish', 'bearish', 'neutral' lists of ReportEntry
    """
    from_date = date(year, 1, 1)
    to_date = date(year, 12, 31)

    # Fetch signals
    signals = search_signals(
        from_date=from_date,
        to_date=to_date,
        limit=limit,
    )

    # Initialize Yahoo client if needed
    yahoo = None
    if fetch_current_prices:
        yahoo = YahooFinanceClient(rate_limit_delay=0.15)

    # Build entries grouped by signal type
    result = {
        "bullish": [],
        "bearish": [],
        "neutral": [],
        "year": str(year),
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "total_signals": len(signals),
    }

    # Track unique tickers to avoid duplicate price fetches
    current_prices = {}

    for i, s in enumerate(signals):
        entry = ReportEntry(
            symbol=s.asset_symbol[:12],
            yahoo_ticker=s.yahoo_ticker,
            entry_price=s.entry_price,
            current_price=None,
            return_pct=None,
            currency=s.entry_price_currency or "",
            source=get_source_name(s),
            speaker=s.speaker_name[:20] if s.speaker_name else "-",
            date_str=s.content_date.strftime("%d %b"),
            signal=s.signal,
        )

        # Fetch current price if we have entry price
        if fetch_current_prices and entry.yahoo_ticker and entry.entry_price:
            if entry.yahoo_ticker not in current_prices:
                try:
                    snapshot = yahoo.get_current_price(entry.yahoo_ticker)
                    if snapshot:
                        current_prices[entry.yahoo_ticker] = snapshot.price
                except Exception as e:
                    logger.debug(f"Failed to fetch current price for {entry.yahoo_ticker}: {e}")

            if entry.yahoo_ticker in current_prices:
                entry.current_price = current_prices[entry.yahoo_ticker]
                entry.return_pct = ((entry.current_price - entry.entry_price) / entry.entry_price) * 100

        # Add to appropriate list
        if s.signal == SignalType.BULLISH:
            result["bullish"].append(entry)
        elif s.signal == SignalType.BEARISH:
            result["bearish"].append(entry)
        else:
            result["neutral"].append(entry)

        # Progress logging
        if (i + 1) % 100 == 0:
            logger.info(f"Processed {i + 1}/{len(signals)} signals...")

    # Sort each list by date (most recent first)
    for key in ["bullish", "bearish", "neutral"]:
        result[key].sort(key=lambda e: e.date_str, reverse=True)

    return result


def format_yearly_report(report: dict) -> str:
    """
    Format full yearly report as text.

    Args:
        report: Output from generate_yearly_report()

    Returns:
        Full formatted report string
    """
    lines = []

    # Header
    lines.append(f"\n{'=' * 70}")
    lines.append(f"  ÅRSRAPPORT: {report['year']}")
    lines.append(f"  Period: {report['from_date']} till {report['to_date']}")
    lines.append(f"  Totalt: {report['total_signals']} signaler")
    lines.append(f"{'=' * 70}\n")

    # Bullish section
    lines.append(f"\n[+] BULLISH ({len(report['bullish'])} st)")
    lines.append("-" * 50)
    lines.append(format_report_table(report["bullish"], "bullish"))

    # Bearish section
    lines.append(f"\n[-] BEARISH ({len(report['bearish'])} st)")
    lines.append("-" * 50)
    lines.append(format_report_table(report["bearish"], "bearish"))

    # Neutral section (optional)
    if report["neutral"]:
        lines.append(f"\n[~] NEUTRAL ({len(report['neutral'])} st)")
        lines.append("-" * 50)
        lines.append(format_report_table(report["neutral"], "neutral"))

    # Summary
    lines.append("\n" + "=" * 70)

    # Calculate accuracy stats
    bullish_with_return = [e for e in report["bullish"] if e.return_pct is not None]
    bearish_with_return = [e for e in report["bearish"] if e.return_pct is not None]

    if bullish_with_return:
        bullish_wins = sum(1 for e in bullish_with_return if e.return_pct > 0)
        bullish_pct = (bullish_wins / len(bullish_with_return)) * 100
        avg_bullish = sum(e.return_pct for e in bullish_with_return) / len(bullish_with_return)
        lines.append(f"  Bullish träffar: {bullish_wins}/{len(bullish_with_return)} ({bullish_pct:.0f}%), snitt: {avg_bullish:+.1f}%")

    if bearish_with_return:
        bearish_wins = sum(1 for e in bearish_with_return if e.return_pct < 0)
        bearish_pct = (bearish_wins / len(bearish_with_return)) * 100
        avg_bearish = sum(e.return_pct for e in bearish_with_return) / len(bearish_with_return)
        lines.append(f"  Bearish träffar: {bearish_wins}/{len(bearish_with_return)} ({bearish_pct:.0f}%), snitt: {avg_bearish:+.1f}%")

    lines.append("=" * 70 + "\n")

    return "\n".join(lines)


def save_report(content: str, output_path: Path) -> Path:
    """
    Save report to file.

    Args:
        content: Report content as string
        output_path: Path to save to

    Returns:
        Path where report was saved
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path
