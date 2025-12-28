"""Summary report generator for PodStock.

This module provides the main interface for generating
summary reports from podcast data.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal, TYPE_CHECKING

from podstock.reports.data_loader import ReportDataLoader
from podstock.reports.models import ReportData
from podstock.reports.prompts import (
    BROAD_SUMMARY_SYSTEM,
    DETAILED_SUMMARY_SYSTEM,
    OPENCODE_INSTRUCTIONS,
    format_broad_prompt,
    format_detailed_prompt,
)

if TYPE_CHECKING:
    from podstock.core.config import Config
    from podstock.core.state import State


class SummaryReportGenerator:
    """Generates summary reports from podcast data.

    Supports two output modes:
    1. Claude Code: Generates a prompt file that can be run in Claude Code
    2. Opencode: Exports JSON with data and instructions for GLM-4.7

    Attributes:
        config: Application configuration.
        state: Episode state manager.
        data_loader: Data loader instance.

    Example:
        >>> generator = SummaryReportGenerator(config, state)
        >>> prompt_path = generator.prepare_for_claude_code(
        ...     start_date=datetime(2025, 12, 20),
        ...     end_date=datetime(2025, 12, 26),
        ...     list_id="broad",
        ...     report_type="broad"
        ... )
    """

    def __init__(self, config: Config, state: State) -> None:
        """Initialize the generator.

        Args:
            config: Application configuration.
            state: Episode state manager.
        """
        self.config = config
        self.state = state
        self.data_loader = ReportDataLoader(config, state)

    def prepare_for_claude_code(
        self,
        start_date: datetime,
        end_date: datetime,
        list_id: str = "broad",
        report_type: Literal["broad", "detailed"] = "broad",
    ) -> Path:
        """Prepare a prompt file for Claude Code.

        Generates a markdown file containing the full prompt
        that can be read and executed by Claude Code.

        Args:
            start_date: Start of period.
            end_date: End of period.
            list_id: Podcast list to use.
            report_type: Type of report.

        Returns:
            Path to the generated prompt file.
        """
        # Load data
        data = self.data_loader.load_for_period(start_date, end_date, list_id)
        data_dict = self._data_to_dict(data)

        # Format prompt
        if report_type == "detailed":
            system_prompt = DETAILED_SUMMARY_SYSTEM
            user_prompt = format_detailed_prompt(data_dict)
        else:
            system_prompt = BROAD_SUMMARY_SYSTEM
            user_prompt = format_broad_prompt(data_dict)

        # Build prompt file content
        content = f"""# Podcast Sammanfattning - {data.period}

**Lista:** {data.list_name}
**Podcasts:** {', '.join(data.podcasts)}
**Avsnitt:** {len(data.episodes)} st
**Rekommendationer:** {len(data.recommendations)} st

---

## Instruktioner

{system_prompt}

---

## Prompt

{user_prompt}

---

## Tips

När du kör denna prompt i Claude Code:
1. Läs igenom datan ovan
2. Generera rapporten enligt instruktionerna
3. Spara resultatet med: `podstock summary save --output rapport.md`

"""

        # Save prompt file
        output_dir = self.config.reports_prompts_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d-%H%M")
        filename = f"{date_str}-{report_type}-prompt.md"
        output_path = output_dir / filename

        output_path.write_text(content)

        return output_path

    def prepare_for_opencode(
        self,
        start_date: datetime,
        end_date: datetime,
        list_id: str = "broad",
        report_type: Literal["broad", "detailed"] = "broad",
    ) -> Path:
        """Prepare a JSON file for Opencode/GLM-4.7.

        Generates a JSON file containing all data and instructions
        that can be loaded into Opencode for processing.

        Args:
            start_date: Start of period.
            end_date: End of period.
            list_id: Podcast list to use.
            report_type: Type of report.

        Returns:
            Path to the generated JSON file.
        """
        # Load data
        data = self.data_loader.load_for_period(start_date, end_date, list_id)
        data_dict = self._data_to_dict(data)

        # Format prompts
        if report_type == "detailed":
            system_prompt = DETAILED_SUMMARY_SYSTEM
            user_prompt = format_detailed_prompt(data_dict)
            detail_level = "detaljerad med citat och djupanalys"
        else:
            system_prompt = BROAD_SUMMARY_SYSTEM
            user_prompt = format_broad_prompt(data_dict)
            detail_level = "koncis men informativ"

        # Build instructions
        instructions = OPENCODE_INSTRUCTIONS.format(
            report_type=report_type,
            detail_level=detail_level,
            period=data.period,
            podcast_count=len(data.podcasts),
            episode_count=len(data.episodes),
            recommendation_count=len(data.recommendations),
        )

        # Build output structure
        output = {
            "instructions": instructions,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "period": data.period,
                "list_id": list_id,
                "list_name": data.list_name,
                "report_type": report_type,
            },
            "data": data_dict,
        }

        # Save JSON file
        output_dir = self.config.reports_prompts_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d-%H%M")
        filename = f"{date_str}-{report_type}-opencode.json"
        output_path = output_dir / filename

        output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))

        return output_path

    def get_available_data(
        self,
        start_date: datetime,
        end_date: datetime,
        list_id: str = "broad",
    ) -> dict:
        """Get summary of available data for a period.

        Useful for checking what data is available before
        generating a full report.

        Args:
            start_date: Start of period.
            end_date: End of period.
            list_id: Podcast list to use.

        Returns:
            Dictionary with summary statistics.
        """
        data = self.data_loader.load_for_period(start_date, end_date, list_id)

        return {
            "period": data.period,
            "list_id": data.list_id,
            "list_name": data.list_name,
            "podcast_count": len(data.podcasts),
            "podcasts": data.podcasts,
            "episode_count": len(data.episodes),
            "episodes_with_transcripts": sum(1 for ep in data.episodes if ep.transcript_available),
            "recommendation_count": len(data.recommendations),
        }

    def save_report(self, content: str, output_path: Path | None = None) -> Path:
        """Save a generated report to file.

        Args:
            content: Report content (markdown).
            output_path: Optional custom path.

        Returns:
            Path to saved report.
        """
        if output_path is None:
            output_dir = self.config.reports_summaries_dir
            output_dir.mkdir(parents=True, exist_ok=True)

            date_str = datetime.now().strftime("%Y-%m-%d-%H%M")
            output_path = output_dir / f"{date_str}-summary.md"
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)

        output_path.write_text(content)
        return output_path

    def _data_to_dict(self, data: ReportData) -> dict:
        """Convert ReportData to serializable dict."""
        return {
            "period": data.period,
            "start_date": data.start_date.isoformat(),
            "end_date": data.end_date.isoformat(),
            "list_id": data.list_id,
            "list_name": data.list_name,
            "podcasts": data.podcasts,
            "episodes": [
                {
                    "episode_id": ep.episode_id,
                    "podcast_id": ep.podcast_id,
                    "podcast_name": ep.podcast_name,
                    "title": ep.title,
                    "published_at": ep.published_at.isoformat(),
                    "transcript_available": ep.transcript_available,
                }
                for ep in data.episodes
            ],
            "recommendations": [
                {
                    "episode_id": rec.episode_id,
                    "podcast_name": rec.podcast_name,
                    "stock": rec.stock,
                    "action": rec.action,
                    "speaker": rec.speaker,
                    "reasoning": rec.reasoning,
                    "quote": rec.quote,
                    "date": rec.date,
                }
                for rec in data.recommendations
            ],
            "generated_at": data.generated_at.isoformat(),
        }
