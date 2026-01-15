"""Test insight schema normalization."""
import pytest


def test_normalize_insight_wrong_schema():
    """Wrong schema (topic/insight) should be transformed to correct (quote/summary)."""
    from podstock.extract.process_transcript import normalize_insight

    wrong_format = {
        "topic": "AI-marknaden",
        "insight": "AI-modeller har blivit en commodity",
        "speaker": "Niklas"
    }

    result = normalize_insight(wrong_format)

    assert "quote" in result
    assert "summary" in result
    assert "category" in result
    assert "tags" in result
    assert result["quote"] == "AI-modeller har blivit en commodity"
    assert result["summary"] == "AI-modeller har blivit en commodity"
    assert result["speaker"] == "Niklas"


def test_normalize_insight_correct_schema():
    """Correct schema should pass through unchanged."""
    from podstock.extract.process_transcript import normalize_insight

    correct_format = {
        "quote": "Jag köper aldrig bolag jag inte förstår",
        "summary": "Investera bara i det du förstår",
        "category": "philosophy",
        "speaker": "Johan",
        "speaker_role": "host",
        "timestamp": "00:15:23",
        "confidence": "high",
        "tags": ["discipline", "understanding"]
    }

    result = normalize_insight(correct_format)

    assert result == correct_format


def test_normalize_analysis_data_with_insights():
    """Full analysis normalization should handle insights array."""
    from podstock.extract.process_transcript import _normalize_analysis_data

    data = {
        "recommendations": [],
        "insights": [
            {"topic": "Test", "insight": "Test insight", "speaker": "A"},
            {"quote": "Correct", "summary": "Correct", "category": "wisdom",
             "speaker": "B", "tags": []}
        ]
    }

    result = _normalize_analysis_data(data)

    # First insight should be normalized
    assert result["insights"][0]["quote"] == "Test insight"
    assert result["insights"][0]["summary"] == "Test insight"
    # Second insight unchanged
    assert result["insights"][1]["quote"] == "Correct"
