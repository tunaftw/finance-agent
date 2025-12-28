"""Pydantic data models for financial filings analysis.

This module defines the core data structures for downloading, parsing,
and analyzing financial reports (10-K, 10-Q, annual reports, etc.).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class FilingType(str, Enum):
    """Type of financial report."""

    ANNUAL_REPORT = "annual"  # Arsredovisning / 10-K
    QUARTERLY_REPORT = "quarterly"  # Kvartalsrapport / 10-Q
    INTERIM_REPORT = "interim"  # Halvarsrapport / 8-K
    CURRENT_REPORT = "current"  # 8-K
    PROSPECTUS = "prospectus"
    PRESENTATION = "presentation"  # Investor presentations
    OTHER = "other"


class FilingSource(str, Enum):
    """Source of the filing."""

    SEC_EDGAR = "sec_edgar"  # US SEC filings via EDGAR
    MANUAL_PDF = "manual_pdf"  # Manually imported PDF
    COMPANY_WEBSITE = "company_website"  # Downloaded from company IR page


class Market(str, Enum):
    """Market/region for the company."""

    US = "us"
    SWEDEN = "sweden"
    EUROPE = "europe"
    OTHER = "other"


class Company(BaseModel):
    """A company whose filings we track.

    Attributes:
        id: Unique identifier (lowercase slug, e.g., "apple-inc", "evolution-gaming").
        name: Full company name.
        ticker: Stock ticker symbol (e.g., "AAPL", "EVO").
        market: Which market/region (us, sweden, europe, other).
        cik: SEC CIK number for US companies (10-digit).
        org_number: Swedish organization number (10-digit).
        added_at: When this company was added.
        active: Whether to include in sync operations.

    Example:
        >>> company = Company(
        ...     id="apple-inc",
        ...     name="Apple Inc.",
        ...     ticker="AAPL",
        ...     market=Market.US,
        ...     cik="0000320193"
        ... )
    """

    id: str = Field(..., min_length=1, pattern=r"^[a-z0-9-]+$")
    name: str = Field(..., min_length=1)
    ticker: str | None = None
    market: Market = Market.US
    cik: str | None = None  # SEC CIK for US companies
    org_number: str | None = None  # Swedish org number
    added_at: datetime = Field(default_factory=datetime.now)
    active: bool = True

    @field_validator("id", mode="before")
    @classmethod
    def normalize_id(cls, v: str) -> str:
        """Normalize ID to lowercase with hyphens."""
        return v.lower().replace(" ", "-").replace("_", "-")

    @field_validator("ticker", mode="before")
    @classmethod
    def normalize_ticker(cls, v: str | None) -> str | None:
        """Normalize ticker to uppercase."""
        return v.upper() if v else None

    @classmethod
    def generate_id(cls, name: str) -> str:
        """Generate a slug ID from company name."""
        import re

        slug = name.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")
        return slug


class Filing(BaseModel):
    """A single financial report/filing.

    Attributes:
        id: Unique identifier (format: "{company_id}-{type}-{year}[-q{quarter}]").
        company_id: Reference to Company.id.
        filing_type: Type of filing (annual, quarterly, etc.).
        fiscal_year: Fiscal year the report covers.
        fiscal_quarter: Quarter number for quarterly reports (1-4).
        filing_date: When the report was filed/published.
        period_end_date: End date of the reporting period.
        source: Where the filing came from (sec_edgar, manual_pdf, etc.).
        source_url: Original URL (EDGAR URL or download source).
        local_path: Path to the downloaded file (PDF/HTML).
        page_count: Number of pages in the document.
        language: Primary language of the document.
        added_at: When this filing was added to our system.
        analyzed: Whether LLM analysis has been completed.

    Example:
        >>> filing = Filing(
        ...     id="apple-inc-annual-2024",
        ...     company_id="apple-inc",
        ...     filing_type=FilingType.ANNUAL_REPORT,
        ...     fiscal_year=2024,
        ...     filing_date=datetime(2024, 10, 31),
        ...     period_end_date=datetime(2024, 9, 28),
        ...     source=FilingSource.SEC_EDGAR
        ... )
    """

    id: str = Field(..., min_length=1)
    company_id: str = Field(..., min_length=1)
    filing_type: FilingType
    fiscal_year: int = Field(..., ge=1990, le=2100)
    fiscal_quarter: int | None = Field(default=None, ge=1, le=4)

    # Dates
    filing_date: datetime
    period_end_date: datetime | None = None

    # Source
    source: FilingSource
    source_url: str | None = None
    local_path: str | None = None  # Relative path within data/filings/raw/

    # Metadata
    page_count: int | None = None
    language: str = "en"
    added_at: datetime = Field(default_factory=datetime.now)
    analyzed: bool = False

    @classmethod
    def generate_id(
        cls,
        company_id: str,
        filing_type: FilingType,
        fiscal_year: int,
        fiscal_quarter: int | None = None,
    ) -> str:
        """Generate a filing ID."""
        base = f"{company_id}-{filing_type.value}-{fiscal_year}"
        if fiscal_quarter:
            base += f"-q{fiscal_quarter}"
        return base

    def generate_filename(self, include_language: bool = True) -> str:
        """Generate a standardized filename for this filing.

        Format: {company_id}_{year}_{type}[_q{quarter}][_{language}].pdf

        Examples:
            - evolution_2024_annual.pdf
            - avanza_2024_quarterly_q2.pdf
            - ericsson_2024_quarterly_q1_sv.pdf

        Args:
            include_language: Whether to include language suffix (if not 'en').

        Returns:
            Standardized filename string.
        """
        parts = [
            self.company_id,
            str(self.fiscal_year),
            self.filing_type.value,
        ]

        if self.fiscal_quarter:
            parts.append(f"q{self.fiscal_quarter}")

        if include_language and self.language != "en":
            parts.append(self.language)

        return "_".join(parts) + ".pdf"


class FinancialMetrics(BaseModel):
    """Extracted financial metrics from a filing.

    All monetary values are in the filing's currency (typically USD or SEK).
    Values are stored as reported (not normalized to millions/billions).

    Attributes:
        filing_id: Reference to Filing.id.
        currency: Currency code (USD, SEK, EUR).
        extracted_at: When these metrics were extracted.
        extraction_method: How metrics were extracted (xbrl, llm, manual).

    Example:
        >>> metrics = FinancialMetrics(
        ...     filing_id="apple-inc-annual-2024",
        ...     currency="USD",
        ...     revenue=394328000000,
        ...     net_income=96995000000
        ... )
    """

    filing_id: str
    currency: str = "USD"
    extracted_at: datetime = Field(default_factory=datetime.now)
    extraction_method: Literal["xbrl", "llm", "manual"] = "llm"

    # Income Statement
    revenue: float | None = None
    cost_of_revenue: float | None = None
    gross_profit: float | None = None
    operating_expenses: float | None = None
    operating_income: float | None = None
    interest_expense: float | None = None
    income_before_tax: float | None = None
    income_tax: float | None = None
    net_income: float | None = None
    eps: float | None = None
    eps_diluted: float | None = None
    shares_outstanding: float | None = None
    shares_diluted: float | None = None

    # Balance Sheet
    total_assets: float | None = None
    current_assets: float | None = None
    cash_and_equivalents: float | None = None
    accounts_receivable: float | None = None
    inventory: float | None = None
    total_liabilities: float | None = None
    current_liabilities: float | None = None
    long_term_debt: float | None = None
    total_debt: float | None = None
    total_equity: float | None = None

    # Cash Flow Statement
    operating_cash_flow: float | None = None
    capex: float | None = None
    free_cash_flow: float | None = None
    dividends_paid: float | None = None
    share_repurchases: float | None = None

    # Calculated Ratios (can be computed or extracted)
    gross_margin: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None
    roe: float | None = None  # Return on Equity
    roa: float | None = None  # Return on Assets
    debt_to_equity: float | None = None
    current_ratio: float | None = None

    def compute_ratios(self) -> None:
        """Compute financial ratios from available metrics."""
        if self.gross_profit and self.revenue:
            self.gross_margin = self.gross_profit / self.revenue

        if self.operating_income and self.revenue:
            self.operating_margin = self.operating_income / self.revenue

        if self.net_income and self.revenue:
            self.net_margin = self.net_income / self.revenue

        if self.net_income and self.total_equity and self.total_equity > 0:
            self.roe = self.net_income / self.total_equity

        if self.net_income and self.total_assets and self.total_assets > 0:
            self.roa = self.net_income / self.total_assets

        if self.total_debt and self.total_equity and self.total_equity > 0:
            self.debt_to_equity = self.total_debt / self.total_equity

        if self.current_assets and self.current_liabilities and self.current_liabilities > 0:
            self.current_ratio = self.current_assets / self.current_liabilities

        if self.operating_cash_flow and self.capex:
            self.free_cash_flow = self.operating_cash_flow - abs(self.capex)


class ManagementTone(str, Enum):
    """Overall tone of management discussion."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    CAUTIOUS = "cautious"
    NEGATIVE = "negative"


class FilingAnalysis(BaseModel):
    """LLM-generated analysis of a filing.

    This contains the synthesized insights from analyzing the full document
    using multi-pass chunking strategy.

    Attributes:
        filing_id: Reference to Filing.id.
        executive_summary: 3-5 sentence summary of the filing.
        key_highlights: Major takeaways (5-7 bullet points).
        risks_mentioned: Key risks identified in the filing.
        opportunities_mentioned: Growth opportunities mentioned.
        yoy_changes: Year-over-year changes in key metrics.
        guidance: Forward-looking guidance if provided.
        management_tone: Overall tone of management discussion.
        notable_quotes: Important quotes from the filing.
        analyzed_at: When analysis was performed.
        model_used: LLM model used for analysis.
        chunks_processed: Number of chunks analyzed.

    Example:
        >>> analysis = FilingAnalysis(
        ...     filing_id="apple-inc-annual-2024",
        ...     executive_summary="Apple reported record services revenue...",
        ...     key_highlights=["Services revenue up 14%", "..."],
        ...     management_tone=ManagementTone.POSITIVE
        ... )
    """

    filing_id: str

    # Summary
    executive_summary: str
    key_highlights: list[str] = Field(default_factory=list)

    # Risks and Opportunities
    risks_mentioned: list[str] = Field(default_factory=list)
    opportunities_mentioned: list[str] = Field(default_factory=list)

    # Comparisons
    yoy_changes: dict[str, str] = Field(default_factory=dict)  # {"revenue": "+5.2%", ...}
    guidance: str | None = None

    # Sentiment
    management_tone: ManagementTone = ManagementTone.NEUTRAL

    # Notable content
    notable_quotes: list[str] = Field(default_factory=list)

    # Metadata
    analyzed_at: datetime = Field(default_factory=datetime.now)
    model_used: str = "claude-sonnet-4-20250514"
    chunks_processed: int = 0
    total_tokens_used: int = 0


class DocumentChunk(BaseModel):
    """A chunk of a document for LLM processing.

    Used internally during multi-pass analysis to track document sections.

    Attributes:
        chunk_id: Unique identifier for this chunk.
        filing_id: Reference to the parent Filing.
        chunk_index: Order of this chunk (0-based).
        page_start: Starting page number (1-based).
        page_end: Ending page number (1-based).
        section_type: Type of section (if identified).
        content: The actual text content of the chunk.
        word_count: Number of words in the chunk.
        has_tables: Whether this chunk contains tables.
        table_data: Extracted table data if present.
    """

    chunk_id: str
    filing_id: str
    chunk_index: int
    page_start: int
    page_end: int
    section_type: str | None = None  # "financial_statements", "mda", "notes", "risk_factors"
    content: str
    word_count: int = 0
    has_tables: bool = False
    table_data: list[dict] | None = None  # Structured table data


class ChunkAnalysis(BaseModel):
    """Analysis result for a single chunk.

    Intermediate result that gets synthesized into FilingAnalysis.
    """

    chunk_id: str
    filing_id: str
    key_points: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    metrics_mentioned: dict[str, str] = Field(default_factory=dict)
    sentiment: ManagementTone = ManagementTone.NEUTRAL
    notable_quotes: list[str] = Field(default_factory=list)


# === File Schema Models ===


class CompaniesFile(BaseModel):
    """Schema for companies.json file.

    Attributes:
        version: Schema version number.
        updated_at: Last update timestamp.
        companies: List of tracked companies.
    """

    version: int = 1
    updated_at: datetime = Field(default_factory=datetime.now)
    companies: list[Company] = Field(default_factory=list)


class PresentationMetadata(BaseModel):
    """Metadata for a downloaded presentation."""

    url: str
    title: str
    year: int
    quarter: int | None = None
    linked_filing_id: str | None = None
    local_path: str
    downloaded_at: datetime = Field(default_factory=datetime.now)


class FilingsStateFile(BaseModel):
    """Schema for filings_state.json file.

    Tracks sync and analysis progress.

    Attributes:
        version: Schema version number.
        last_sync: Last sync timestamp.
        filings: Dictionary mapping filing_id to Filing.
        analyzed_filings: Set of filing IDs that have been analyzed.
        presentations: Dictionary mapping presentation_id to PresentationMetadata.
    """

    version: int = 1
    last_sync: datetime | None = None
    last_updated: datetime = Field(default_factory=datetime.now)
    filings: dict[str, Filing] = Field(default_factory=dict)
    analyzed_filings: list[str] = Field(default_factory=list)
    presentations: dict[str, PresentationMetadata] = Field(default_factory=dict)
