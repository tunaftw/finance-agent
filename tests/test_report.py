"""Tests for report module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from podstock.core.models import ConfidenceLevel, Recommendation
from podstock.report.markdown import (
    calculate_stats,
    generate_and_save_report,
    generate_report,
    save_report,
)


def make_recommendation(
    company_name: str = "Test Company",
    episode_id: str = "bp-2024-12-18",
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    **kwargs,
) -> Recommendation:
    """Create a test recommendation."""
    defaults = {
        "id": f"{episode_id}-001",
        "episode_id": episode_id,
        "company_name": company_name,
        "quote": "Test quote",
        "context": "Test context",
        "reasoning": "Test reasoning",
        "confidence": confidence,
        "extracted_at": datetime.now(),
    }
    defaults.update(kwargs)
    return Recommendation(**defaults)


class TestCalculateStats:
    """Tests for calculate_stats function."""

    def test_empty_recommendations(self) -> None:
        """Returns zero counts for empty list."""
        stats = calculate_stats([])

        assert stats.total_recommendations == 0
        assert stats.by_podcast == {}
        assert stats.by_company == {}
        assert stats.by_confidence == {}

    def test_single_recommendation(self) -> None:
        """Calculates stats for single recommendation."""
        recs = [make_recommendation("Apple", "bp-2024-12-18")]

        stats = calculate_stats(recs)

        assert stats.total_recommendations == 1
        assert stats.by_company == {"Apple": 1}
        assert stats.by_confidence == {"medium": 1}

    def test_multiple_recommendations(self) -> None:
        """Calculates stats for multiple recommendations."""
        recs = [
            make_recommendation("Apple", "bp-2024-12-18", ConfidenceLevel.HIGH),
            make_recommendation("Apple", "bp-2024-12-19", ConfidenceLevel.HIGH),
            make_recommendation("Google", "bp-2024-12-18", ConfidenceLevel.LOW),
        ]

        stats = calculate_stats(recs)

        assert stats.total_recommendations == 3
        assert stats.by_company == {"Apple": 2, "Google": 1}
        assert stats.by_confidence == {"high": 2, "low": 1}

    def test_groups_by_podcast(self) -> None:
        """Groups by podcast ID from episode_id."""
        recs = [
            make_recommendation("A", "bp-2024-12-18"),
            make_recommendation("B", "bp-2024-12-19"),
            make_recommendation("C", "ip-2024-12-18"),
        ]

        stats = calculate_stats(recs)

        assert stats.by_podcast == {"bp": 2, "ip": 1}

    def test_date_range(self) -> None:
        """Calculates date range from extracted_at."""
        early = datetime(2024, 1, 1)
        late = datetime(2024, 12, 31)

        recs = [
            make_recommendation("A", extracted_at=early),
            make_recommendation("B", extracted_at=late),
        ]

        stats = calculate_stats(recs)

        assert stats.date_range == (early, late)


class TestGenerateReport:
    """Tests for generate_report function."""

    def test_empty_recommendations(self) -> None:
        """Generates report for empty list."""
        report = generate_report([])

        assert "PodStock" in report
        assert "No recommendations" in report

    def test_includes_title(self) -> None:
        """Includes custom title."""
        report = generate_report([], title="Custom Title")

        assert "# Custom Title" in report

    def test_includes_stats(self) -> None:
        """Includes statistics section by default."""
        recs = [make_recommendation("Apple")]

        report = generate_report(recs)

        assert "## Summary" in report
        assert "Total recommendations" in report

    def test_excludes_stats_when_disabled(self) -> None:
        """Excludes statistics when include_stats=False."""
        recs = [make_recommendation("Apple")]

        report = generate_report(recs, include_stats=False)

        assert "## Summary" not in report

    def test_includes_recommendation_details(self) -> None:
        """Includes recommendation details."""
        recs = [
            make_recommendation(
                company_name="Apple Inc",
                ticker="AAPL",
                quote="Apple är ett bra köp",
                confidence=ConfidenceLevel.HIGH,
            )
        ]

        report = generate_report(recs)

        assert "Apple Inc" in report
        assert "AAPL" in report
        assert "Apple är ett bra köp" in report
        assert "High" in report

    def test_groups_by_podcast(self) -> None:
        """Groups recommendations by podcast."""
        recs = [
            make_recommendation("A", "bp-2024-12-18"),
            make_recommendation("B", "ip-2024-12-18"),
        ]

        report = generate_report(recs, group_by_podcast=True)

        assert "### BP" in report
        assert "### IP" in report

    def test_confidence_badges(self) -> None:
        """Includes confidence badges."""
        recs = [
            make_recommendation("A", confidence=ConfidenceLevel.HIGH),
            make_recommendation("B", confidence=ConfidenceLevel.LOW),
        ]

        report = generate_report(recs)

        assert "High" in report
        assert "Low" in report

    def test_includes_host_if_present(self) -> None:
        """Includes host name if present."""
        recs = [make_recommendation("A", host="John Doe")]

        report = generate_report(recs)

        assert "John Doe" in report

    def test_includes_time_horizon_if_present(self) -> None:
        """Includes time horizon if present."""
        recs = [make_recommendation("A", time_horizon="1-2 years")]

        report = generate_report(recs)

        assert "1-2 years" in report


class TestSaveReport:
    """Tests for save_report function."""

    def test_creates_file(self, tmp_path: Path) -> None:
        """Creates report file."""
        report = "# Test Report\n\nContent here."
        output_path = tmp_path / "report.md"

        result = save_report(report, output_path)

        assert result == output_path
        assert output_path.exists()
        assert output_path.read_text(encoding="utf-8") == report

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        """Creates parent directories if needed."""
        report = "# Test"
        output_path = tmp_path / "reports" / "2024" / "report.md"

        result = save_report(report, output_path)

        assert result.exists()

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        """Overwrites existing file."""
        output_path = tmp_path / "report.md"
        output_path.write_text("Old content", encoding="utf-8")

        save_report("New content", output_path)

        assert output_path.read_text(encoding="utf-8") == "New content"


class TestGenerateAndSaveReport:
    """Tests for generate_and_save_report function."""

    def test_generates_and_saves(self, tmp_path: Path) -> None:
        """Generates and saves report."""
        recs = [make_recommendation("Apple")]

        result = generate_and_save_report(recs, tmp_path)

        assert result.exists()
        assert result.suffix == ".md"

        content = result.read_text(encoding="utf-8")
        assert "Apple" in content

    def test_uses_custom_filename(self, tmp_path: Path) -> None:
        """Uses custom filename when provided."""
        recs = [make_recommendation("Apple")]

        result = generate_and_save_report(
            recs, tmp_path, filename="custom.md"
        )

        assert result.name == "custom.md"

    def test_default_filename_includes_date(self, tmp_path: Path) -> None:
        """Default filename includes current date."""
        recs = [make_recommendation("Apple")]

        result = generate_and_save_report(recs, tmp_path)

        today = datetime.now().strftime("%Y-%m-%d")
        assert today in result.name
