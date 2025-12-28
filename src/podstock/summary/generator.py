"""Guest summary report generator."""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


class SummaryGenerator:
    """Generates guest summary reports from extracted recommendations."""

    def __init__(self, extracted_path: Path):
        self.extracted_path = extracted_path
        self.recommendations = self._load_recommendations()

    def _load_recommendations(self) -> list[dict]:
        """Load recommendations from JSON file."""
        recs_file = self.extracted_path / "recommendations.json"
        if not recs_file.exists():
            return []
        return json.loads(recs_file.read_text())

    def generate_guest_table(self, podcast_filter: str | None = None) -> str:
        """Generate guest recommendations table with Date + Podcast."""
        # Group by speaker (exclude "Host")
        by_speaker: dict[str, list[dict]] = defaultdict(list)
        for r in self.recommendations:
            speaker = r.get("speaker", "Unknown")
            if speaker and speaker != "Host":
                if podcast_filter and podcast_filter.lower() not in r.get("podcast", "").lower():
                    continue
                by_speaker[speaker].append(r)

        if not by_speaker:
            return "Inga gäst-rekommendationer hittades.\n"

        lines = [
            "## Gäst-Rekommendationer per Talare\n",
            "| Gäst | Datum | Podcast | Köp | Sälj/Undvik | Sektor |",
            "|------|-------|---------|-----|-------------|--------|",
        ]

        # Sort speakers by number of recommendations
        sorted_speakers = sorted(by_speaker.items(), key=lambda x: len(x[1]), reverse=True)

        for speaker, recs in sorted_speakers:
            # Get date and podcast (all recs from same episode have same date/podcast)
            dates = sorted(set(r.get("date", "?") for r in recs))
            date_str = dates[0] if len(dates) == 1 else f"{dates[0]} - {dates[-1]}"
            podcasts = sorted(set(r.get("podcast", "?") for r in recs))
            podcast_str = ", ".join(podcasts)

            # Group by action
            buys = [r["stock"] for r in recs if r.get("action") == "buy"]
            sells = [r["stock"] for r in recs if r.get("action") == "sell"]
            avoids = [r["stock"] for r in recs if r.get("action") == "avoid"]

            buy_str = ", ".join(buys) if buys else "-"
            sell_avoid = sells + [f"{s} ⛔" for s in avoids]
            sell_str = ", ".join(sell_avoid) if sell_avoid else "-"

            # Determine sector from recommendations
            sectors = set()
            for r in recs:
                if r.get("sector"):
                    sectors.add(r["sector"])
            sector_str = ", ".join(sorted(sectors)) if sectors else "-"

            lines.append(f"| **{speaker}** | {date_str} | {podcast_str} | {buy_str} | {sell_str} | {sector_str} |")

        return "\n".join(lines) + "\n"

    def generate_buy_recommendations(self, podcast_filter: str | None = None) -> str:
        """Generate list of all buy recommendations."""
        buys = [r for r in self.recommendations if r.get("action") == "buy"]

        if podcast_filter:
            buys = [r for r in buys if podcast_filter.lower() in r.get("podcast", "").lower()]

        if not buys:
            return "Inga köprekommendationer hittades.\n"

        # Sort by date descending
        buys = sorted(buys, key=lambda x: x.get("date", ""), reverse=True)

        lines = [
            f"## Alla Köprekommendationer ({len(buys)} st)\n",
            "| Datum | Aktie | Talare | Podcast | Motivering |",
            "|-------|-------|--------|---------|------------|",
        ]

        for r in buys:
            date = r.get("date", "?")
            stock = r.get("stock", "?")
            speaker = r.get("speaker", "?")
            podcast = r.get("podcast", "?")
            reasoning = r.get("reasoning", "")[:60] + "..." if len(r.get("reasoning", "")) > 60 else r.get("reasoning", "")

            lines.append(f"| {date} | **{stock}** | {speaker} | {podcast} | {reasoning} |")

        return "\n".join(lines) + "\n"

    def generate_stats(self, podcast_filter: str | None = None) -> str:
        """Generate statistics section."""
        recs = self.recommendations
        if podcast_filter:
            recs = [r for r in recs if podcast_filter.lower() in r.get("podcast", "").lower()]

        if not recs:
            return "Ingen data tillgänglig.\n"

        # Count by action
        by_action: dict[str, int] = defaultdict(int)
        for r in recs:
            by_action[r.get("action", "unknown")] += 1

        # Count by podcast
        by_podcast: dict[str, int] = defaultdict(int)
        for r in recs:
            by_podcast[r.get("podcast", "Unknown")] += 1

        lines = [
            "## Statistik\n",
            f"- **Totalt:** {len(recs)} rekommendationer",
            f"- **Köp:** {by_action.get('buy', 0)} | **Sälj:** {by_action.get('sell', 0)} | **Hold:** {by_action.get('hold', 0)} | **Watch:** {by_action.get('watch', 0)} | **Avoid:** {by_action.get('avoid', 0)}",
            "",
            "**Per Podcast:**",
        ]

        for podcast, count in sorted(by_podcast.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"- {podcast}: {count}")

        return "\n".join(lines) + "\n"

    def generate_top_stocks(self, n: int = 15, podcast_filter: str | None = None) -> str:
        """Generate top N most mentioned stocks."""
        recs = self.recommendations
        if podcast_filter:
            recs = [r for r in recs if podcast_filter.lower() in r.get("podcast", "").lower()]

        if not recs:
            return "Ingen data tillgänglig.\n"

        # Count mentions per stock
        stock_counts: dict[str, dict] = defaultdict(lambda: {"count": 0, "latest_action": None, "latest_date": ""})

        for r in recs:
            stock = r.get("stock", "Unknown")
            stock_counts[stock]["count"] += 1
            if r.get("date", "") > stock_counts[stock]["latest_date"]:
                stock_counts[stock]["latest_date"] = r.get("date", "")
                stock_counts[stock]["latest_action"] = r.get("action", "?").upper()

        # Sort by count
        sorted_stocks = sorted(stock_counts.items(), key=lambda x: x[1]["count"], reverse=True)[:n]

        lines = [
            f"## Topp {n} Mest Omnämnda Aktier\n",
            "| # | Aktie | Omnämnanden | Senaste Action |",
            "|---|-------|-------------|----------------|",
        ]

        for i, (stock, data) in enumerate(sorted_stocks, 1):
            lines.append(f"| {i} | {stock} | {data['count']} | {data['latest_action']} |")

        return "\n".join(lines) + "\n"

    def generate_full_report(self, podcast_filter: str | None = None) -> str:
        """Generate complete summary report."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        title = "# PodStock Gäst-Sammanfattning"
        if podcast_filter:
            title += f" - {podcast_filter}"

        sections = [
            title,
            f"Genererad: {now}\n",
            "---\n",
            self.generate_guest_table(podcast_filter),
            "---\n",
            self.generate_buy_recommendations(podcast_filter),
            "---\n",
            self.generate_stats(podcast_filter),
            "---\n",
            self.generate_top_stocks(15, podcast_filter),
        ]

        return "\n".join(sections)

    def save(self, output_dir: Path, filename: str | None = None, podcast_filter: str | None = None) -> Path:
        """Save report to dated .md file."""
        output_dir.mkdir(parents=True, exist_ok=True)

        if filename:
            output_path = output_dir / filename
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")
            output_path = output_dir / f"{date_str}-guest-summary.md"

        report = self.generate_full_report(podcast_filter)
        output_path.write_text(report)

        return output_path
