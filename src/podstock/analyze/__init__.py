"""Analysis module for PodStock.

This module provides:
- Prompt building for Claude analysis
- Parsing Claude's JSON responses
- Saving/loading recommendations
"""

from __future__ import annotations

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
    save_recommendations,
)

__all__ = [
    # Prompt builder
    "build_analysis_prompt",
    "build_summary_prompt",
    "chunk_transcript",
    "load_template",
    # Result parser
    "extract_json_from_response",
    "load_recommendations",
    "parse_claude_response",
    "save_recommendations",
]
