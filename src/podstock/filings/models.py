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


# === Deep Analysis Models ===


class CEOLetterTone(str, Enum):
    """Tone of CEO/Chairman letter."""

    OPTIMISTIC = "optimistic"
    CAUTIOUSLY_OPTIMISTIC = "cautiously_optimistic"
    NEUTRAL = "neutral"
    CAUTIOUS = "cautious"
    DEFENSIVE = "defensive"


class ConfidenceLevel(str, Enum):
    """Confidence level in statements."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AttributionType(str, Enum):
    """Attribution for challenges/issues."""

    EXTERNAL = "external"  # Market conditions, macro, competitors
    INTERNAL = "internal"  # Execution, mistakes, delays
    MIXED = "mixed"


class ChallengeAttribution(BaseModel):
    """A challenge mentioned with its attribution."""

    challenge: str
    attribution: AttributionType
    tone: str = "explanatory"  # explanatory, defensive, dismissive, accountable


class Promise(BaseModel):
    """A forward-looking commitment made by management."""

    statement: str
    metric: str | None = None  # organic_growth, operating_margin, etc.
    target: str | None = None  # "4-6%", "15%", etc.
    timeframe: str | None = None  # "FY 2024", "Q2 2025", "medium_term"
    confidence_language: str = "expect"  # expect, target, aim, hope, will


class Theme(BaseModel):
    """A strategic theme discussed in the letter."""

    topic: str
    emphasis: str = "medium"  # high, medium, low
    sentiment: str = "neutral"  # positive, neutral, negative, improving, declining


class KeyQuote(BaseModel):
    """A notable quote from the letter."""

    quote: str
    category: str = "general"  # commitment, vision, warning, achievement, excuse


class CEOLetterAnalysis(BaseModel):
    """Deep analysis of CEO/Chairman letter.

    Extracts tone, promises, themes, challenges, and honesty signals
    from the CEO letter section of annual/quarterly reports.
    """

    author: str | None = None
    title: str | None = None  # "CEO", "President", "Chairman"
    word_count: int = 0

    # Tone analysis
    tone: CEOLetterTone = CEOLetterTone.NEUTRAL
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM

    # Forward-looking statements
    promises: list[Promise] = Field(default_factory=list)

    # Strategic themes
    themes: list[Theme] = Field(default_factory=list)

    # Challenges and attribution
    challenges: list[ChallengeAttribution] = Field(default_factory=list)

    # Honesty signals (positive indicators of transparent communication)
    honesty_signals: list[str] = Field(default_factory=list)

    # Notable quotes
    key_quotes: list[KeyQuote] = Field(default_factory=list)

    # Q&A format detection (common in Swedish reports)
    is_qa_format: bool = False
    questions_addressed: list[str] = Field(default_factory=list)


class SegmentPerformance(BaseModel):
    """Performance data for a business segment."""

    name: str
    revenue: float | None = None
    revenue_growth_yoy: float | None = None  # As decimal, e.g., 0.08 for 8%
    operating_margin: float | None = None
    order_intake: float | None = None
    order_intake_growth_yoy: float | None = None
    management_commentary: str | None = None
    outlook: str = "neutral"  # positive, neutral, cautious, negative
    management_focus: str = "medium"  # high, medium, low


class MDAAnalysis(BaseModel):
    """Management Discussion & Analysis extraction.

    Captures key narratives, segment commentary, and management's
    interpretation of results.
    """

    key_narratives: list[str] = Field(default_factory=list)
    management_interpretation: str | None = None

    # Segment-level commentary
    segment_commentary: dict[str, SegmentPerformance] = Field(default_factory=dict)

    # Key operational highlights
    operational_highlights: list[str] = Field(default_factory=list)

    # Concerns or challenges mentioned
    concerns_mentioned: list[str] = Field(default_factory=list)


class RiskSeverity(str, Enum):
    """Severity level of a risk."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskChange(str, Enum):
    """Change in risk status from previous filing."""

    NEW = "new"
    ESCALATED = "escalated"
    UNCHANGED = "unchanged"
    DE_ESCALATED = "de-escalated"
    REMOVED = "removed"


class RiskFactor(BaseModel):
    """A specific risk factor from the filing."""

    risk: str
    severity: RiskSeverity = RiskSeverity.MEDIUM
    category: str | None = None  # regulatory, operational, market, financial, legal
    change: RiskChange = RiskChange.UNCHANGED
    previous_severity: RiskSeverity | None = None
    is_boilerplate: bool = False


class RiskFactorAnalysis(BaseModel):
    """Analysis of risk factors section.

    Tracks new, removed, and changed risks compared to previous filing.
    """

    risks: list[RiskFactor] = Field(default_factory=list)

    # Summary counts
    new_risks_count: int = 0
    removed_risks_count: int = 0
    escalated_risks_count: int = 0

    # Boilerplate ratio (higher = less informative)
    boilerplate_ratio: float = 0.0

    # Key risk themes
    top_risk_categories: list[str] = Field(default_factory=list)


class GuidanceChange(str, Enum):
    """Change in guidance from previous period."""

    RAISED = "raised"
    MAINTAINED = "maintained"
    LOWERED = "lowered"
    WITHDRAWN = "withdrawn"
    NEW = "new"


class GuidanceTarget(BaseModel):
    """A specific guidance target."""

    metric: str  # organic_growth, operating_margin, eps, revenue
    value: str  # "4-6%", "15%", ">12%"
    period: str  # "FY 2024", "medium_term", "2024-2028"
    vs_previous: GuidanceChange = GuidanceChange.MAINTAINED
    notes: str | None = None


class GuidanceAnalysis(BaseModel):
    """Forward-looking guidance extraction.

    Captures specific targets and how they compare to previous guidance.
    """

    targets: list[GuidanceTarget] = Field(default_factory=list)

    # Overall direction
    overall_direction: GuidanceChange = GuidanceChange.MAINTAINED

    # Commentary on guidance
    commentary: str | None = None

    # Confidence in guidance
    management_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class AuditorOpinion(str, Enum):
    """Type of auditor opinion."""

    UNQUALIFIED = "unqualified"
    QUALIFIED = "qualified"
    ADVERSE = "adverse"
    DISCLAIMER = "disclaimer"


class AuditorNotes(BaseModel):
    """Auditor's report analysis.

    Captures opinion type and any concerns or emphasis of matter.
    """

    opinion_type: AuditorOpinion = AuditorOpinion.UNQUALIFIED
    concerns: list[str] = Field(default_factory=list)
    emphasis_of_matter: list[str] = Field(default_factory=list)
    key_audit_matters: list[str] = Field(default_factory=list)


class DeepFilingAnalysis(BaseModel):
    """Complete deep analysis of a filing.

    Extends the basic FilingAnalysis with section-by-section deep extraction
    including CEO letter, MD&A, risk factors, segments, and guidance.

    This is the main output model for the deep analysis pipeline.
    """

    # Identification
    filing_id: str
    company_id: str
    filing_type: FilingType
    fiscal_year: int
    fiscal_quarter: int | None = None

    # Metadata
    analyzed_at: datetime = Field(default_factory=datetime.now)
    model_used: str = "claude-sonnet-4-20250514"
    analysis_version: str = "2.0"  # Deep analysis version

    # Basic analysis (from original FilingAnalysis)
    executive_summary: str = ""
    key_highlights: list[str] = Field(default_factory=list)

    # Financial metrics
    financial_metrics: FinancialMetrics | None = None

    # Deep section analysis
    ceo_letter: CEOLetterAnalysis | None = None
    mda_analysis: MDAAnalysis | None = None
    risk_factors: RiskFactorAnalysis | None = None
    segment_reporting: list[SegmentPerformance] = Field(default_factory=list)
    guidance: GuidanceAnalysis | None = None
    auditor_notes: AuditorNotes | None = None

    # Overall signals
    management_tone: ManagementTone = ManagementTone.NEUTRAL
    notable_quotes: list[str] = Field(default_factory=list)

    # Processing metadata
    chunks_processed: int = 0
    total_tokens_used: int = 0
    sections_found: list[str] = Field(default_factory=list)  # Which sections were detected


class PromiseStatus(str, Enum):
    """Status of a tracked promise."""

    ON_TRACK = "on_track"
    PARTIALLY_MET = "partially_met"
    MET = "met"
    MISSED = "missed"
    DELAYED = "delayed"
    UNKNOWN = "unknown"


class TrackedPromise(BaseModel):
    """A promise tracked across multiple filings."""

    promise: str
    metric: str | None = None
    target: str | None = None
    made_in: str  # Filing ID where promise was made
    current_status: PromiseStatus = PromiseStatus.UNKNOWN
    evidence: str | None = None
    mentions: list[str] = Field(default_factory=list)  # Filing IDs where mentioned


class ToneDataPoint(BaseModel):
    """Tone at a specific point in time."""

    period: str  # "Q3 2024", "Annual 2023"
    tone: CEOLetterTone
    confidence: ConfidenceLevel
    reasoning: str | None = None  # Why this tone rating
    key_quote: str | None = None  # Supporting CEO quote


class ThemeEvolution(BaseModel):
    """Evolution of a theme over time."""

    theme: str
    trend: str  # increasing, decreasing, stable
    interpretation: str | None = None


class FinancialTrendPoint(BaseModel):
    """A single data point in a financial trend."""

    period: str
    value: float


class FinancialTrend(BaseModel):
    """Financial metric trend over time."""

    metric: str
    values: list[FinancialTrendPoint] = Field(default_factory=list)
    cagr: float | None = None  # Compound annual growth rate
    trajectory: str = "stable"  # improving, stable, declining


class GuidanceAccuracyRecord(BaseModel):
    """Historical record of guidance accuracy."""

    year: int
    metric: str
    guided: str
    actual: str
    status: PromiseStatus


class WatchItem(BaseModel):
    """Detailed risk item for watch list."""

    description: str  # Risk description
    severity: str = "medium"  # high, medium, low
    category: str = "unknown"  # external, operational, regulatory, financial, market, legal
    source_filing: str = ""  # Filing ID where identified
    change: str = "new"  # escalated, de-escalated, new, removed, unchanged


class EvolutionSignals(BaseModel):
    """Synthesized signals from evolution analysis."""

    green_flags: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    watch_items: list[WatchItem] = Field(default_factory=list)  # Detailed risk items


class FilingEvolution(BaseModel):
    """Cross-filing evolution synthesis.

    Tracks how a company's narrative, promises, and metrics evolve
    across multiple filings.
    """

    company_id: str
    last_updated: datetime = Field(default_factory=datetime.now)
    filings_analyzed: list[str] = Field(default_factory=list)

    # Promise tracking
    promise_tracker: list[TrackedPromise] = Field(default_factory=list)

    # Tone trajectory
    tone_trajectory: list[ToneDataPoint] = Field(default_factory=list)

    # Theme evolution
    theme_evolution: list[ThemeEvolution] = Field(default_factory=list)

    # Financial trends
    financial_trends: dict[str, FinancialTrend] = Field(default_factory=dict)

    # Guidance accuracy
    guidance_accuracy: list[GuidanceAccuracyRecord] = Field(default_factory=list)
    accuracy_rate: float | None = None  # Overall accuracy rate

    # Synthesized signals
    signals: EvolutionSignals = Field(default_factory=EvolutionSignals)


class InvestmentVerdict(str, Enum):
    """Investment thesis verdict based on evolution analysis."""

    GREEN = "green"  # Strong buy signal - credibility high, trends positive
    YELLOW = "yellow"  # Mixed signals - watch closely
    RED = "red"  # Warning flags - credibility issues or negative trends


class InvestmentThesis(BaseModel):
    """Investment thesis generated from evolution analysis.

    Synthesizes CEO credibility scoring, trend analysis, and signals
    into an actionable investment verdict.

    CEO Credibility Score Formula (0-100):
    - Promise delivery rate: 40%
    - Guidance accuracy: 30%
    - Tone consistency: 20%
    - Challenge attribution: 10%
    """

    company_id: str
    generated_at: datetime = Field(default_factory=datetime.now)

    # Core verdict
    verdict: InvestmentVerdict = InvestmentVerdict.YELLOW
    verdict_reasoning: str = ""

    # CEO Credibility
    ceo_credibility_score: float = 50.0  # 0-100
    credibility_breakdown: dict[str, float] = Field(default_factory=dict)

    # Key signals
    green_flags: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    watch_items: list[WatchItem] = Field(default_factory=list)  # Detailed risk items

    # Trend summaries
    tone_trend: str = "stable"  # improving, stable, declining
    margin_trend: str = "stable"
    growth_trend: str = "stable"
    leverage_assessment: str = "healthy"  # healthy, elevated, concerning

    # Promise tracking summary
    promises_met: int = 0
    promises_missed: int = 0
    promises_pending: int = 0

    # Investment philosophy alignment (user's 17 principles)
    philosophy_alignment: dict[str, str] = Field(default_factory=dict)
