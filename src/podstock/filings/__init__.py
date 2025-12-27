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
    # Models
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
]
