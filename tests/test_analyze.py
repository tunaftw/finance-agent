"""Tests for analyze module."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from podstock.analyze.prompt_builder import (
    build_analysis_prompt,
    build_summary_prompt,
    chunk_transcript,
    load_template,
)
from podstock.analyze.result_parser import (
    extract_json_from_response,
    load_recommendations,
    parse_claude_response,
    parse_confidence,
    parse_recommendation,
    save_recommendations,
)
from podstock.core.exceptions import AnalysisError
from podstock.core.models import ConfidenceLevel, Recommendation


class TestLoadTemplate:
    """Tests for load_template function."""

    def test_load_existing_template(self, tmp_path: Path) -> None:
        """Loads template from file."""
        template_path = tmp_path / "template.md"
        template_path.write_text("Analyze: {{TRANSCRIPT}}", encoding="utf-8")

        result = load_template(template_path)

        assert result == "Analyze: {{TRANSCRIPT}}"

    def test_load_missing_template_raises_error(self, tmp_path: Path) -> None:
        """Raises AnalysisError for missing template."""
        template_path = tmp_path / "missing.md"

        with pytest.raises(AnalysisError, match="not found"):
            load_template(template_path)


class TestChunkTranscript:
    """Tests for chunk_transcript function."""

    def test_short_transcript_single_chunk(self) -> None:
        """Short transcript returns single chunk."""
        transcript = "This is a short transcript."

        result = chunk_transcript(transcript, chunk_size=1000)

        assert len(result) == 1
        assert result[0] == transcript

    def test_long_transcript_multiple_chunks(self) -> None:
        """Long transcript is split into chunks."""
        # Create a transcript that's longer than chunk_size
        transcript = "A" * 100000

        result = chunk_transcript(transcript, chunk_size=50000, overlap=1000)

        assert len(result) >= 2

    def test_chunk_default_size(self) -> None:
        """Uses default chunk size."""
        transcript = "Short text."

        result = chunk_transcript(transcript)

        assert len(result) == 1


class TestBuildAnalysisPrompt:
    """Tests for build_analysis_prompt function."""

    def test_build_with_custom_template(self, tmp_path: Path) -> None:
        """Builds prompt using template."""
        template_path = tmp_path / "template.md"
        template_path.write_text(
            "Analyze: {{TRANSCRIPT}}\nPodcast: {{PODCAST_NAME}}\n"
            "Date: {{EPISODE_DATE}}\nHosts: {{HOSTS}}",
            encoding="utf-8",
        )

        result = build_analysis_prompt(
            transcript="Hello world.",
            podcast_name="Test Podcast",
            episode_title="Episode 1",
            episode_date="2024-12-18",
            hosts=["Host A", "Host B"],
            template_path=template_path,
        )

        assert "Hello world." in result
        assert "Test Podcast" in result
        assert "2024-12-18" in result
        assert "Host A, Host B" in result

    def test_build_with_datetime_date(self, tmp_path: Path) -> None:
        """Handles datetime objects for date."""
        template_path = tmp_path / "template.md"
        template_path.write_text("Date: {{EPISODE_DATE}}", encoding="utf-8")

        result = build_analysis_prompt(
            transcript="Text",
            podcast_name="Podcast",
            episode_title="Title",
            episode_date=datetime(2024, 12, 18),
            template_path=template_path,
        )

        assert "2024-12-18" in result

    def test_build_without_hosts(self, tmp_path: Path) -> None:
        """Uses 'Okänd' when no hosts provided."""
        template_path = tmp_path / "template.md"
        template_path.write_text("Hosts: {{HOSTS}}", encoding="utf-8")

        result = build_analysis_prompt(
            transcript="Text",
            podcast_name="Podcast",
            episode_title="Title",
            episode_date="2024-12-18",
            template_path=template_path,
        )

        assert "Okänd" in result


class TestBuildSummaryPrompt:
    """Tests for build_summary_prompt function."""

    def test_build_summary_prompt(self) -> None:
        """Builds summary prompt with partial results."""
        partial_results = [
            '{"recommendations": [{"company_name": "Apple"}]}',
            '{"recommendations": [{"company_name": "Google"}]}',
        ]

        result = build_summary_prompt(
            partial_results=partial_results,
            podcast_name="Test Podcast",
            episode_title="Episode 1",
        )

        assert "Test Podcast" in result
        assert "Episode 1" in result
        assert "Apple" in result
        assert "Google" in result


class TestExtractJsonFromResponse:
    """Tests for extract_json_from_response function."""

    def test_extract_raw_json(self) -> None:
        """Extracts raw JSON object."""
        response = '{"recommendations": []}'

        result = extract_json_from_response(response)

        assert result == '{"recommendations": []}'

    def test_extract_from_code_block(self) -> None:
        """Extracts JSON from markdown code block."""
        response = """Here are the recommendations:

```json
{"recommendations": [{"company_name": "Apple"}]}
```

That's all!"""

        result = extract_json_from_response(response)

        assert "recommendations" in result
        assert "Apple" in result

    def test_extract_from_code_block_no_language(self) -> None:
        """Extracts JSON from code block without language tag."""
        response = """Results:

```
{"recommendations": []}
```"""

        result = extract_json_from_response(response)

        assert "recommendations" in result

    def test_no_json_raises_error(self) -> None:
        """Raises error when no JSON found."""
        response = "No JSON here, just text."

        with pytest.raises(AnalysisError, match="No valid JSON"):
            extract_json_from_response(response)


class TestParseConfidence:
    """Tests for parse_confidence function."""

    def test_parse_high(self) -> None:
        """Parses 'high' to HIGH."""
        assert parse_confidence("high") == ConfidenceLevel.HIGH

    def test_parse_medium(self) -> None:
        """Parses 'medium' to MEDIUM."""
        assert parse_confidence("medium") == ConfidenceLevel.MEDIUM

    def test_parse_low(self) -> None:
        """Parses 'low' to LOW."""
        assert parse_confidence("low") == ConfidenceLevel.LOW

    def test_parse_case_insensitive(self) -> None:
        """Parsing is case-insensitive."""
        assert parse_confidence("HIGH") == ConfidenceLevel.HIGH
        assert parse_confidence("Medium") == ConfidenceLevel.MEDIUM

    def test_parse_none_defaults_to_medium(self) -> None:
        """None defaults to MEDIUM."""
        assert parse_confidence(None) == ConfidenceLevel.MEDIUM

    def test_parse_unknown_defaults_to_medium(self) -> None:
        """Unknown values default to MEDIUM."""
        assert parse_confidence("unknown") == ConfidenceLevel.MEDIUM


class TestParseRecommendation:
    """Tests for parse_recommendation function."""

    def test_parse_valid_recommendation(self) -> None:
        """Parses valid recommendation data."""
        data = {
            "company_name": "Apple Inc",
            "ticker": "AAPL",
            "market": "NASDAQ",
            "quote": "Apple är ett bra köp",
            "context": "Diskussion om tech-aktier",
            "reasoning": "Stark tillväxt",
            "confidence": "high",
        }

        result = parse_recommendation(data, "bp-2024-12-18", 1)

        assert result is not None
        assert result.company_name == "Apple Inc"
        assert result.ticker == "AAPL"
        assert result.confidence == ConfidenceLevel.HIGH
        assert result.id == "bp-2024-12-18-001"

    def test_parse_missing_required_returns_none(self) -> None:
        """Returns None if required fields missing."""
        data = {
            "company_name": "Apple",
            # Missing quote, context, reasoning
        }

        result = parse_recommendation(data, "bp-2024-12-18", 1)

        assert result is None

    def test_parse_minimal_valid(self) -> None:
        """Parses with only required fields."""
        data = {
            "company_name": "Apple",
            "quote": "Buy Apple",
            "context": "Stock discussion",
            "reasoning": "Good company",
        }

        result = parse_recommendation(data, "test-ep", 1)

        assert result is not None
        assert result.company_name == "Apple"
        assert result.ticker is None


class TestParseClaudeResponse:
    """Tests for parse_claude_response function."""

    def test_parse_valid_response(self) -> None:
        """Parses valid Claude response."""
        response = json.dumps({
            "recommendations": [
                {
                    "company_name": "Apple",
                    "quote": "Buy Apple",
                    "context": "Discussion",
                    "reasoning": "Growth",
                },
            ]
        })

        result = parse_claude_response(response, "test-ep")

        assert len(result) == 1
        assert result[0].company_name == "Apple"

    def test_parse_empty_recommendations(self) -> None:
        """Returns empty list for no recommendations."""
        response = '{"recommendations": []}'

        result = parse_claude_response(response, "test-ep")

        assert result == []

    def test_parse_invalid_json_raises_error(self) -> None:
        """Raises error for invalid JSON."""
        response = "not valid json"

        with pytest.raises(AnalysisError, match="No valid JSON"):
            parse_claude_response(response, "test-ep")

    def test_parse_invalid_structure_raises_error(self) -> None:
        """Raises error if recommendations is not a list."""
        response = '{"recommendations": "not a list"}'

        with pytest.raises(AnalysisError, match="must be a list"):
            parse_claude_response(response, "test-ep")


class TestSaveAndLoadRecommendations:
    """Tests for save_recommendations and load_recommendations."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """Saves recommendations to JSON file."""
        recommendations = [
            Recommendation(
                id="bp-2024-12-18-001",
                episode_id="bp-2024-12-18",
                company_name="Apple",
                quote="Buy Apple",
                context="Discussion",
                reasoning="Growth",
                confidence=ConfidenceLevel.HIGH,
                extracted_at=datetime.now(),
            )
        ]

        result = save_recommendations(
            recommendations, tmp_path, "bp", "bp-2024-12-18"
        )

        assert result.exists()
        assert result.suffix == ".json"

    def test_save_creates_podcast_directory(self, tmp_path: Path) -> None:
        """Creates podcast subdirectory."""
        recommendations = [
            Recommendation(
                id="test-001",
                episode_id="test-ep",
                company_name="Test",
                quote="Test",
                context="Test",
                reasoning="Test",
                confidence=ConfidenceLevel.MEDIUM,
                extracted_at=datetime.now(),
            )
        ]

        save_recommendations(
            recommendations, tmp_path, "new-podcast", "test-ep"
        )

        assert (tmp_path / "new-podcast").is_dir()

    def test_roundtrip(self, tmp_path: Path) -> None:
        """Saved recommendations can be loaded."""
        original = [
            Recommendation(
                id="bp-2024-12-18-001",
                episode_id="bp-2024-12-18",
                company_name="Apple",
                ticker="AAPL",
                quote="Buy Apple",
                context="Discussion",
                reasoning="Growth",
                confidence=ConfidenceLevel.HIGH,
                extracted_at=datetime.now(),
            )
        ]

        save_recommendations(original, tmp_path, "bp", "bp-2024-12-18")
        loaded = load_recommendations(tmp_path, "bp", "bp-2024-12-18")

        assert len(loaded) == 1
        assert loaded[0].company_name == "Apple"
        assert loaded[0].ticker == "AAPL"
        assert loaded[0].confidence == ConfidenceLevel.HIGH

    def test_load_missing_raises_error(self, tmp_path: Path) -> None:
        """Raises error for missing file."""
        with pytest.raises(AnalysisError, match="not found"):
            load_recommendations(tmp_path, "missing", "missing-ep")
