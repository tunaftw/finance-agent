"""Orchestration run reports.

Provides structured reporting for podcast pipeline runs,
including terminal output, markdown reports, and persistence.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class TranscriptDownload:
    """Record of a downloaded transcript."""

    filename: str
    destination: str
    source: str  # "apple" or "whisper"


@dataclass
class AnalysisResult:
    """Record of an analysis."""

    filename: str
    destination: str
    recommendations: int
    stock_segments: int
    insights: int


@dataclass
class ImprovementObservation:
    """Observed issue that could be improved.

    Categories:
    - critical: Schema-fel, trasig pipeline
    - quality: Saknade insights, dåliga citat
    - optimization: Timeout-justering, cache-miss
    - skill: Prompt kunde vara tydligare
    """

    category: str  # critical/quality/optimization/skill
    description: str
    suggested_fix: str
    file_path: str | None
    auto_fixable: bool
    evidence: str


@dataclass
class OrchestrationReport:
    """Complete report of an orchestration run."""

    timestamp: datetime = field(default_factory=datetime.now)
    model_used: str = ""

    # Downloads
    transcripts: list[TranscriptDownload] = field(default_factory=list)

    # Analyses
    analyses: list[AnalysisResult] = field(default_factory=list)

    # Totals
    total_recommendations: int = 0
    total_segments: int = 0
    total_insights: int = 0
    new_tickers: list[str] = field(default_factory=list)

    # Timing
    timing: dict[str, float] = field(default_factory=dict)

    # Improvements
    improvements: list[ImprovementObservation] = field(default_factory=list)

    def add_transcript(self, filename: str, destination: str, source: str) -> None:
        """Add a downloaded transcript."""
        self.transcripts.append(TranscriptDownload(filename, destination, source))

    def add_analysis(
        self, filename: str, destination: str, recs: int, segs: int, ins: int
    ) -> None:
        """Add an analysis result."""
        self.analyses.append(AnalysisResult(filename, destination, recs, segs, ins))
        self.total_recommendations += recs
        self.total_segments += segs
        self.total_insights += ins

    def add_improvement(
        self,
        category: str,
        description: str,
        suggested_fix: str,
        file_path: str | None = None,
        auto_fixable: bool = False,
        evidence: str = "",
    ) -> None:
        """Add an improvement observation."""
        self.improvements.append(
            ImprovementObservation(
                category=category,
                description=description,
                suggested_fix=suggested_fix,
                file_path=file_path,
                auto_fixable=auto_fixable,
                evidence=evidence,
            )
        )

    def to_terminal(self) -> str:
        """Format report for terminal output."""
        lines = [
            "═" * 65,
            f"KÖRNINGSRAPPORT - {self.timestamp.strftime('%Y-%m-%d %H:%M')}",
            "═" * 65,
            "",
        ]

        # Downloads
        if self.transcripts:
            lines.append(f"NEDLADDADE TRANSKRIPT ({len(self.transcripts)} st)")
            for t in self.transcripts:
                source_icon = "[Apple]" if t.source == "apple" else "[Whisper]"
                lines.append(f"   {source_icon} {t.filename}")
                lines.append(f"      -> {t.destination}")
            lines.append("")

        # Analyses
        if self.analyses:
            lines.append(f"ANALYSER ({len(self.analyses)} st, modell: {self.model_used})")
            for a in self.analyses:
                lines.append(f"   * {a.filename}")
                lines.append(
                    f"     {a.recommendations} recs, {a.stock_segments} segments, {a.insights} insights"
                )
            lines.append("")

        # Summary
        lines.append("SAMMANFATTNING")
        lines.append(f"   Totalt rekommendationer: {self.total_recommendations}")
        lines.append(f"   Totalt stock_segments:   {self.total_segments}")
        lines.append(f"   Totalt insights:         {self.total_insights}")
        if self.new_tickers:
            lines.append(f"   Nya tickers:             {', '.join(self.new_tickers)}")
        lines.append("")

        # Timing
        if self.timing:
            lines.append("TIMING")
            total = sum(self.timing.values())
            for step, duration in self.timing.items():
                if duration >= 60:
                    time_str = f"{int(duration // 60)}m {int(duration % 60)}s"
                else:
                    time_str = f"{int(duration)}s"
                lines.append(f"   {step}: {time_str}")
            if total >= 60:
                lines.append(f"   Total: {int(total // 60)}m {int(total % 60)}s")
            lines.append("")

        # Improvements
        if self.improvements:
            lines.append("FÖRBÄTTRINGSFÖRSLAG")
            for i, imp in enumerate(self.improvements, 1):
                icon = {
                    "critical": "[!]",
                    "quality": "[?]",
                    "optimization": "[+]",
                    "skill": "[~]",
                }.get(imp.category, "[ ]")
                lines.append(f"   {icon} {i}. {imp.description}")
                lines.append(f"      Förslag: {imp.suggested_fix}")
            lines.append("")

        lines.append("═" * 65)

        return "\n".join(lines)

    def to_markdown(self) -> str:
        """Format report as markdown for file storage."""
        lines = [
            f"# Körningsrapport {self.timestamp.strftime('%Y-%m-%d %H:%M')}",
            "",
            f"**Modell:** {self.model_used}",
            "",
        ]

        # Downloads
        if self.transcripts:
            lines.append(f"## Nedladdade transkript ({len(self.transcripts)} st)")
            lines.append("")
            lines.append("| Fil | Destination | Källa |")
            lines.append("|-----|-------------|-------|")
            for t in self.transcripts:
                lines.append(f"| {t.filename} | {t.destination} | {t.source} |")
            lines.append("")

        # Analyses
        if self.analyses:
            lines.append(f"## Analyser ({len(self.analyses)} st)")
            lines.append("")
            lines.append("| Fil | Recs | Segments | Insights |")
            lines.append("|-----|------|----------|----------|")
            for a in self.analyses:
                lines.append(
                    f"| {a.filename} | {a.recommendations} | {a.stock_segments} | {a.insights} |"
                )
            lines.append("")

        # Summary
        lines.append("## Sammanfattning")
        lines.append("")
        lines.append(f"- **Totalt rekommendationer:** {self.total_recommendations}")
        lines.append(f"- **Totalt stock_segments:** {self.total_segments}")
        lines.append(f"- **Totalt insights:** {self.total_insights}")
        if self.new_tickers:
            lines.append(f"- **Nya tickers:** {', '.join(self.new_tickers)}")
        lines.append("")

        # Timing
        if self.timing:
            lines.append("## Timing")
            lines.append("")
            lines.append("| Steg | Tid |")
            lines.append("|------|-----|")
            for step, duration in self.timing.items():
                if duration >= 60:
                    time_str = f"{int(duration // 60)}m {int(duration % 60)}s"
                else:
                    time_str = f"{int(duration)}s"
                lines.append(f"| {step} | {time_str} |")
            lines.append("")

        # Improvements
        if self.improvements:
            lines.append("## Förbättringsförslag")
            lines.append("")
            for imp in self.improvements:
                lines.append(f"### [{imp.category.upper()}] {imp.description}")
                lines.append("")
                lines.append(f"**Förslag:** {imp.suggested_fix}")
                if imp.file_path:
                    lines.append(f"**Fil:** `{imp.file_path}`")
                lines.append(f"**Auto-fix:** {'Ja' if imp.auto_fixable else 'Nej'}")
                if imp.evidence:
                    lines.append(f"**Bevis:** {imp.evidence}")
                lines.append("")
        else:
            lines.append("## Förbättringsförslag")
            lines.append("")
            lines.append("_Inga observerade problem denna körning._")
            lines.append("")

        return "\n".join(lines)

    def save(self, logs_dir: Path | None = None) -> Path:
        """Save report to logs/orchestration/ directory."""
        if logs_dir is None:
            logs_dir = Path("logs/orchestration")
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Save timestamped file
        filename = f"{self.timestamp.strftime('%Y-%m-%dT%H-%M-%S')}.md"
        filepath = logs_dir / filename
        filepath.write_text(self.to_markdown(), encoding="utf-8")

        # Update latest symlink/copy
        latest = logs_dir / "latest.md"
        latest.write_text(self.to_markdown(), encoding="utf-8")

        return filepath
