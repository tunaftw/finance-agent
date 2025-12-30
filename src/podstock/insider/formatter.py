"""Output formatting for insider transaction data.

Formats InsiderReport data for display in CLI and skill output.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from podstock.insider.models import InsiderReport, InsiderTransaction


def _format_value(value: float, currency: str) -> str:
    """Format monetary value with appropriate suffix."""
    if currency == "USD":
        symbol = "$"
        suffix = ""
    elif currency == "SEK":
        symbol = ""
        suffix = " SEK"
    else:
        symbol = ""
        suffix = f" {currency}"

    if value >= 1_000_000:
        formatted = f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        formatted = f"{value / 1_000:.0f}K"
    else:
        formatted = f"{value:.0f}"

    if currency == "USD":
        return f"{symbol}{formatted}"
    return f"{formatted}{suffix}"


def _format_shares(shares: int) -> str:
    """Format share count with thousands separator."""
    return f"{shares:,}"


def format_transaction_row(tx: InsiderTransaction) -> str:
    """Format a single transaction as a table row."""
    date_str = tx.transaction_date.strftime("%Y-%m-%d")
    role = tx.role.value.upper()
    tx_type = tx.transaction_type.value.upper()
    shares = _format_shares(tx.shares)
    value = _format_value(tx.total_value, tx.currency)

    return f"| {date_str} | {tx.insider_name} | {role} | {tx_type} | {shares} | {value} |"


def format_report(report: InsiderReport) -> str:
    """Format an insider report for display."""
    lines = [
        f"## Insider Activity: {report.ticker} ({report.company_name})",
        f"Period: Last {report.period_days} days | Market: {report.market}",
        "",
    ]

    if not report.transactions:
        lines.append("No transactions found in this period.")
        return "\n".join(lines)

    # Table header
    lines.extend([
        "| Date | Insider | Role | Type | Shares | Value |",
        "|------|---------|------|------|--------|-------|",
    ])

    # Transaction rows
    for tx in report.transactions:
        lines.append(format_transaction_row(tx))

    # Summary
    buys = [t for t in report.transactions if t.transaction_type.value == "buy"]
    sells = [t for t in report.transactions if t.transaction_type.value == "sell"]

    buy_total = sum(t.total_value for t in buys)
    sell_total = sum(t.total_value for t in sells)
    net = buy_total - sell_total

    currency = report.transactions[0].currency if report.transactions else "USD"
    net_str = _format_value(abs(net), currency)
    signal = "bullish" if net > 0 else "bearish" if net < 0 else "neutral"

    lines.extend([
        "",
        f"**Summary:** {len(buys)} buys, {len(sells)} sells | "
        f"Net: {'+' if net > 0 else '-'}{net_str} ({signal} signal)",
    ])

    return "\n".join(lines)


def format_portfolio_scan(
    results: list[tuple[InsiderReport, dict | None]],
) -> str:
    """Format portfolio scan results."""
    if not results:
        return "## Portfolio Insider Scan\n\nNo stocks to scan. Add recommendations first."

    total = len(results)
    with_activity = [r for r, _ in results if r.transactions]

    lines = [
        "## Portfolio Insider Scan",
        f"Checked {total} stocks with active recommendations",
        "",
    ]

    if with_activity:
        lines.append("### Notable Activity")
        for report, _context in results:
            if not report.transactions:
                continue

            buys = [t for t in report.transactions if t.transaction_type.value == "buy"]
            sells = [t for t in report.transactions if t.transaction_type.value == "sell"]

            if buys:
                buy_total = sum(t.total_value for t in buys)
                currency = buys[0].currency
                lines.append(
                    f"- **{report.ticker}**: {len(buys)} insider(s) bought "
                    f"{_format_value(buy_total, currency)}"
                )
            if sells:
                sell_total = sum(t.total_value for t in sells)
                currency = sells[0].currency
                lines.append(
                    f"- **{report.ticker}**: {len(sells)} insider(s) sold "
                    f"{_format_value(sell_total, currency)}"
                )
        lines.append("")

    tickers_without_activity = [r.ticker for r, _ in results if not r.transactions]
    if tickers_without_activity:
        lines.append(f"**No insider activity:** {', '.join(tickers_without_activity[:5])}")
        if len(tickers_without_activity) > 5:
            lines.append(f"  ...and {len(tickers_without_activity) - 5} others")

    return "\n".join(lines)
