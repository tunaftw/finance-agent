"""Shared pytest fixtures for PodStock tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory structure."""
    (tmp_path / "audio").mkdir()
    (tmp_path / "transcripts").mkdir()
    (tmp_path / "recommendations").mkdir()
    (tmp_path / "reports").mkdir()
    return tmp_path
