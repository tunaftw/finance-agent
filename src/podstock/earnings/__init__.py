"""Earnings call transcript collection and analysis.

This module provides functionality for:
- Scraping earnings call transcripts from Inderes.fi/Inderes.se
- Storing transcripts with linking to related filings
- LLM-powered analysis with bullish/bearish signal extraction
- Interactive Q&A on transcripts

Note:
    Inderes loads full transcript content with JavaScript.
    The scraper uses Playwright for browser automation to extract full transcripts.
    Install with: pip install playwright && playwright install chromium

Example:
    >>> from podstock.earnings import InderesScraper, EarningsStorage
    >>> from podstock.core.config import load_config
    >>>
    >>> config = load_config()
    >>> storage = EarningsStorage(config)
    >>> scraper = InderesScraper()
    >>>
    >>> # Find and sync transcripts
    >>> listings = scraper.find_transcripts(company_name="Nordea")
    >>> for listing in listings:
    ...     transcript = scraper.fetch_transcript(listing)
    ...     if transcript:
    ...         storage.save_transcript(transcript)

See Also:
    podstock.filings: Related financial document analysis (annual reports, quarterly reports)
    podstock.analyze: Prompt building utilities for LLM analysis
"""

from podstock.earnings.models import (
    EarningsTranscript,
    GuidanceChange,
    GuidanceItem,
    ManagementTone,
    Signal,
    SignalType,
    Speaker,
    TranscriptAnalysis,
    TranscriptListing,
)
from podstock.earnings.playwright_scraper import PlaywrightInderesScraper
from podstock.earnings.storage import EarningsStorage

# Alias for backwards compatibility
InderesScraper = PlaywrightInderesScraper

__all__ = [
    # Models
    "EarningsTranscript",
    "GuidanceChange",
    "GuidanceItem",
    "ManagementTone",
    "Signal",
    "SignalType",
    "Speaker",
    "TranscriptAnalysis",
    "TranscriptListing",
    # Scraper
    "InderesScraper",  # Alias for PlaywrightInderesScraper
    "PlaywrightInderesScraper",
    # Storage
    "EarningsStorage",
]
