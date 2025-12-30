"""LLM-based filing analysis.

This package provides tools for analyzing financial filings using LLMs.

Modules:
- ceo_letter: CEO/Chairman letter section finder and prompts
- deep_analysis: Section finders and prompts for deep analysis

NOTE: No Anthropic API calls are made from this module.
Analysis is done via:
- Claude Code: Reading sections and analyzing in conversation
- OpenCode/GLM-4.7: Via scripts/filings_glm_driver.py
"""

from podstock.filings.analysis.ceo_letter import (
    CEO_LETTER_EXTRACTION_PROMPT,
    SWEDISH_CEO_LETTER_PROMPT,
    extract_json_from_response,
    find_ceo_letter_section,
)
from podstock.filings.analysis.deep_analysis import (
    FULL_FILING_ANALYSIS_PROMPT,
    GUIDANCE_EXTRACTION_PROMPT,
    MDA_ANALYSIS_PROMPT,
    RISK_FACTORS_PROMPT,
    SEGMENT_ANALYSIS_PROMPT,
    find_guidance_section,
    find_mda_section,
    find_risk_factors_section,
    find_section,
    find_segment_section,
)
from podstock.filings.analysis.evolution import (
    load_evolution,
    save_evolution,
    synthesize_evolution,
)
from podstock.filings.analysis.thesis import (
    generate_thesis,
    load_thesis,
    save_thesis,
)

__all__ = [
    # CEO Letter
    "find_ceo_letter_section",
    "CEO_LETTER_EXTRACTION_PROMPT",
    "SWEDISH_CEO_LETTER_PROMPT",
    # Deep Analysis
    "find_section",
    "find_mda_section",
    "find_risk_factors_section",
    "find_guidance_section",
    "find_segment_section",
    "MDA_ANALYSIS_PROMPT",
    "RISK_FACTORS_PROMPT",
    "GUIDANCE_EXTRACTION_PROMPT",
    "SEGMENT_ANALYSIS_PROMPT",
    "FULL_FILING_ANALYSIS_PROMPT",
    # Utility
    "extract_json_from_response",
    # Evolution
    "synthesize_evolution",
    "save_evolution",
    "load_evolution",
    # Thesis
    "generate_thesis",
    "save_thesis",
    "load_thesis",
]
