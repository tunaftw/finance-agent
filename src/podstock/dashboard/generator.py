"""Dashboard generator for static HTML visualization."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .exporters import (
    export_analyses,
    export_filings,
    export_podcasts,
    export_recommendations,
    export_sources,
    export_twitter,
    export_youtube,
)


@dataclass
class GenerateResult:
    """Result of dashboard generation."""

    output_path: Path
    files_generated: int
    analyses_count: int
    recommendations_count: int
    podcast_episodes_count: int
    tweets_count: int
    youtube_videos_count: int


class DashboardGenerator:
    """Generates static HTML dashboard from database and data files."""

    def __init__(self, db_path: Path, output_dir: Path, data_dir: Path | None = None):
        self.db_path = db_path
        self.output_dir = output_dir
        self.json_data_dir = output_dir / "data"  # Output JSON data directory
        self.assets_dir = output_dir / "assets"
        # Source data directory (for podcast/twitter/youtube JSON files)
        self.source_data_dir = data_dir or db_path.parent

    def generate(self, full_rebuild: bool = False) -> GenerateResult:
        """Generate the complete dashboard.

        Args:
            full_rebuild: If True, regenerate all data even if unchanged.

        Returns:
            GenerateResult with statistics about the generation.
        """
        from podstock.db.engine import get_engine, get_session

        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.json_data_dir.mkdir(exist_ok=True)
        self.assets_dir.mkdir(exist_ok=True)

        files_generated = 0

        engine = get_engine(self.db_path)

        with get_session(engine) as session:
            # Export database data (for Inbox tab)
            analyses = export_analyses(session)
            self._write_json("analyses.json", analyses)
            files_generated += 1

            recommendations = export_recommendations(session)
            self._write_json("recommendations.json", recommendations)
            files_generated += 1

            sources = export_sources(session)
            self._write_json("sources.json", sources)
            files_generated += 1

            # Export source-specific data from JSON files (with session for price data)
            podcasts = export_podcasts(self.source_data_dir, session=session)
            self._write_json("podcasts.json", podcasts)
            files_generated += 1

            twitter = export_twitter(self.source_data_dir, session=session)
            self._write_json("twitter.json", twitter)
            files_generated += 1

            youtube = export_youtube(self.source_data_dir, session=session)
            self._write_json("youtube.json", youtube)
            files_generated += 1

        # Export filings evolution and thesis data (no session needed)
        filings = export_filings(self.source_data_dir)
        self._write_json("filings.json", filings)
        files_generated += 1

        # Add metadata
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "db_path": str(self.db_path),
            "counts": {
                "analyses": len(analyses),
                "recommendations": len(recommendations),
                "sources": len(sources),
                "podcast_episodes": len(podcasts["episodes"]),
                "tweets": len(twitter["tweets"]),
                "youtube_videos": len(youtube["videos"]),
                "filings_companies": len(filings["companies"]),
            },
        }
        self._write_json("metadata.json", metadata)
        files_generated += 1

        # Build inline data for HTML embedding
        inline_data = {
            "metadata": metadata,
            "analyses": analyses,
            "recommendations": recommendations,
            "sources": sources,
            "podcasts": podcasts,
            "twitter": twitter,
            "youtube": youtube,
            "filings": filings,
        }

        # Copy HTML template and assets with inline data
        self._copy_templates(inline_data)
        files_generated += 3  # index.html, styles.css, app.js

        return GenerateResult(
            output_path=self.output_dir / "index.html",
            files_generated=files_generated,
            analyses_count=len(analyses),
            recommendations_count=len(recommendations),
            podcast_episodes_count=len(podcasts["episodes"]),
            tweets_count=len(twitter["tweets"]),
            youtube_videos_count=len(youtube["videos"]),
        )

    def _write_json(self, filename: str, data: Any) -> None:
        """Write data to JSON file."""
        path = self.json_data_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _copy_templates(self, inline_data: dict[str, Any] | None = None) -> None:
        """Copy HTML templates and assets to output directory.

        Args:
            inline_data: Optional dict of data to embed inline in HTML.
                         This avoids CORS issues with file:// protocol.
        """
        templates_dir = Path(__file__).parent / "templates"

        # Process index.html with inline data
        src_html = templates_dir / "index.html"
        if src_html.exists():
            html_content = src_html.read_text(encoding="utf-8")

            if inline_data:
                # Inject inline data as a script tag before </head>
                data_script = f"""<script>
// Inline data embedded by dashboard generator (avoids CORS issues with file://)
window.DASHBOARD_DATA = {json.dumps(inline_data, ensure_ascii=False)};
</script>
"""
                html_content = html_content.replace("</head>", f"{data_script}</head>")

            (self.output_dir / "index.html").write_text(html_content, encoding="utf-8")

        # Copy assets
        src_assets = templates_dir / "assets"
        if src_assets.exists():
            for asset in src_assets.iterdir():
                shutil.copy(asset, self.assets_dir / asset.name)
