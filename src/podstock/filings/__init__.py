"""Financial filings analysis module.

This module provides functionality for downloading, parsing, and analyzing
financial reports (10-K, 10-Q, annual reports, quarterly reports).

Supported sources:
- SEC EDGAR (US companies) via EdgarTools
- Manual PDF import (any company)

Key features:
- Multi-pass chunking to handle large PDFs without filling context
- XBRL parsing for structured financial data (SEC filings)
- LLM-based analysis for insights and summaries
- Table extraction from PDFs

Example:
    >>> from podstock.filings import FilingsClient, FilingAnalyzer
    >>> from podstock.filings.models import Company, FilingType
    >>>
    >>> # Add a company
    >>> client = FilingsClient(data_dir)
    >>> client.add_company("AAPL", market="us")
    >>>
    >>> # Sync filings from EDGAR
    >>> filings = client.sync_filings("apple-inc", limit=3)
    >>>
    >>> # Analyze a filing
    >>> analyzer = FilingAnalyzer(api_key)
    >>> analysis = analyzer.analyze(filings[0])
"""

from podstock.filings.exceptions import (
    AnalysisError,
    ChunkingError,
    CompanyNotFoundError,
    FilingNotFoundError,
    FilingsError,
    PDFParseError,
    XBRLParseError,
)
from podstock.filings.models import (
    # Core models
    ChunkAnalysis,
    Company,
    DocumentChunk,
    Filing,
    FilingAnalysis,
    FilingSource,
    FilingType,
    FinancialMetrics,
    ManagementTone,
    Market,
    # Deep analysis models
    CEOLetterAnalysis,
    CEOLetterTone,
    ChallengeAttribution,
    ConfidenceLevel,
    DeepFilingAnalysis,
    FilingEvolution,
    GuidanceAnalysis,
    KeyQuote,
    MDAAnalysis,
    Promise,
    RiskFactorAnalysis,
    SegmentPerformance,
    Theme,
)
from podstock.filings.analysis import (
    CEO_LETTER_EXTRACTION_PROMPT,
    FULL_FILING_ANALYSIS_PROMPT,
    GUIDANCE_EXTRACTION_PROMPT,
    MDA_ANALYSIS_PROMPT,
    RISK_FACTORS_PROMPT,
    SEGMENT_ANALYSIS_PROMPT,
    SWEDISH_CEO_LETTER_PROMPT,
    extract_json_from_response,
    find_ceo_letter_section,
    find_guidance_section,
    find_mda_section,
    find_risk_factors_section,
    find_section,
    find_segment_section,
)

__all__ = [
    # Exceptions
    "FilingsError",
    "FilingNotFoundError",
    "CompanyNotFoundError",
    "PDFParseError",
    "XBRLParseError",
    "ChunkingError",
    "AnalysisError",
    # Core Models
    "FilingType",
    "FilingSource",
    "Market",
    "Company",
    "Filing",
    "FinancialMetrics",
    "FilingAnalysis",
    "ManagementTone",
    "DocumentChunk",
    "ChunkAnalysis",
    # Deep Analysis Models
    "CEOLetterTone",
    "ConfidenceLevel",
    "Promise",
    "Theme",
    "ChallengeAttribution",
    "KeyQuote",
    "CEOLetterAnalysis",
    "MDAAnalysis",
    "RiskFactorAnalysis",
    "SegmentPerformance",
    "GuidanceAnalysis",
    "DeepFilingAnalysis",
    "FilingEvolution",
    # Section Finders
    "find_ceo_letter_section",
    "find_section",
    "find_mda_section",
    "find_risk_factors_section",
    "find_guidance_section",
    "find_segment_section",
    # Prompt Templates
    "CEO_LETTER_EXTRACTION_PROMPT",
    "SWEDISH_CEO_LETTER_PROMPT",
    "MDA_ANALYSIS_PROMPT",
    "RISK_FACTORS_PROMPT",
    "GUIDANCE_EXTRACTION_PROMPT",
    "SEGMENT_ANALYSIS_PROMPT",
    "FULL_FILING_ANALYSIS_PROMPT",
    # Utility
    "extract_json_from_response",
]
