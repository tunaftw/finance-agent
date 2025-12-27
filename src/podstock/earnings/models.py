"""Pydantic data models for earnings call transcripts.

This module defines the core data structures for:
- Earnings call transcripts from various sources
- LLM analysis results with bullish/bearish signals
- Guidance tracking and follow-up items
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ManagementTone(str, Enum):
    """Overall tone of management during earnings call."""

    VERY_CONFIDENT = "very_confident"
    CONFIDENT = "confident"
    NEUTRAL = "neutral"
    CAUTIOUS = "cautious"
    DEFENSIVE = "defensive"


class GuidanceChange(str, Enum):
    """Direction of guidance change."""

    RAISED = "raised"
    REAFFIRMED = "reaffirmed"
    LOWERED = "lowered"
    WITHDRAWN = "withdrawn"
    NEW = "new"


class SignalType(str, Enum):
    """Type of signal (bullish or bearish)."""

    BULLISH = "bullish"
    BEARISH = "bearish"


class Speaker(BaseModel):
    """A speaker in an earnings call.

    Attributes:
        name: Full name of the speaker.
        role: Job title or role (CEO, CFO, Analyst, etc.).
        company: Company affiliation (for analysts).
    """

    name: str
    role: str | None = None
    company: str | None = None


class TranscriptListing(BaseModel):
    """A transcript listing from the scraper (before fetching full content).

    Attributes:
        url: Full URL to the transcript page.
        title: Title of the transcript.
        company_name: Name of the company.
        date: Date of the earnings call.
        quarter: Fiscal quarter (1-4).
        year: Fiscal year.
    """

    url: str
    title: str
    company_name: str
    date: datetime | None = None
    quarter: int | None = None
    year: int | None = None


class EarningsTranscript(BaseModel):
    """A raw earnings call transcript.

    Attributes:
        id: Unique identifier (format: "{company_id}-earnings-{year}-q{quarter}").
        company_id: Internal company ID (matches filings).
        company_name: Full company name.
        ticker: Stock ticker symbol.
        fiscal_year: Fiscal year of the earnings call.
        fiscal_quarter: Quarter number (1-4).
        call_date: Date and time of the earnings call.
        language: Primary language ("en", "sv", "mixed").
        full_text: Complete transcript text.
        word_count: Number of words in the transcript.
        speakers: List of identified speakers.
        source: Source of the transcript ("inderes", "company_website", etc.).
        source_url: Original URL where transcript was fetched.
        local_path: Relative path to saved file (if stored locally).
        linked_filing_id: ID of the linked quarterly/annual report.
        linked_presentation_id: ID of the linked presentation.
        collected_at: When this transcript was collected.

    Example:
        >>> transcript = EarningsTranscript(
        ...     id="nordea-earnings-2024-q3",
        ...     company_id="nordea",
        ...     company_name="Nordea Bank Abp",
        ...     ticker="NDA-FI",
        ...     fiscal_year=2024,
        ...     fiscal_quarter=3,
        ...     call_date=datetime(2024, 10, 17),
        ...     language="en",
        ...     full_text="Good morning everyone...",
        ...     word_count=15000,
        ...     source="inderes",
        ...     source_url="https://www.inderes.fi/en/transcripts/nordea-q3-2024"
        ... )
    """

    id: str = Field(..., min_length=1)
    company_id: str = Field(..., min_length=1)
    company_name: str = Field(..., min_length=1)
    ticker: str | None = None

    fiscal_year: int = Field(..., ge=2000, le=2100)
    fiscal_quarter: int = Field(..., ge=1, le=4)
    call_date: datetime
    language: str = "en"

    # Content
    full_text: str = Field(..., min_length=1)
    word_count: int = Field(default=0, ge=0)

    # Speakers (if identified)
    speakers: list[Speaker] = Field(default_factory=list)

    # Source
    source: str = "inderes"
    source_url: str
    local_path: str | None = None

    # Linking to filings
    linked_filing_id: str | None = None
    linked_presentation_id: str | None = None

    collected_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def generate_id(
        cls,
        company_id: str,
        fiscal_year: int,
        fiscal_quarter: int,
    ) -> str:
        """Generate a unique transcript ID.

        Args:
            company_id: Slugified company identifier (e.g., 'nordea', 'hacksaw').
            fiscal_year: Fiscal year (e.g., 2024).
            fiscal_quarter: Fiscal quarter (1-4).

        Returns:
            ID in format "{company_id}-earnings-{year}-q{quarter}".

        Example:
            >>> EarningsTranscript.generate_id("nordea", 2024, 3)
            'nordea-earnings-2024-q3'
        """
        return f"{company_id}-earnings-{fiscal_year}-q{fiscal_quarter}"

    def compute_word_count(self) -> None:
        """Compute and set word_count from full_text.

        Splits full_text on whitespace and counts the resulting tokens.
        Updates the word_count attribute in-place.
        """
        self.word_count = len(self.full_text.split())


class GuidanceItem(BaseModel):
    """A specific guidance item from management.

    Attributes:
        metric: What metric the guidance is for (revenue, margin, etc.).
        value: The guidance value or range.
        period: Time period the guidance covers (FY2024, Q4 2024, etc.).
        change: Direction of change from previous guidance.
        notes: Additional context.
    """

    metric: str
    value: str
    period: str | None = None
    change: GuidanceChange = GuidanceChange.REAFFIRMED
    notes: str | None = None


class Signal(BaseModel):
    """A bullish or bearish signal extracted from the transcript.

    Attributes:
        signal_type: Whether this is bullish or bearish.
        category: Category of signal (growth, margins, market, risk, etc.).
        description: Description of the signal.
        quote: Direct quote from transcript supporting this signal.
        confidence: Confidence level (high, medium, low).
    """

    signal_type: SignalType
    category: str
    description: str
    quote: str | None = None
    confidence: Literal["high", "medium", "low"] = "medium"


class AnalystQuestion(BaseModel):
    """A question from an analyst during Q&A.

    Attributes:
        analyst_name: Name of the analyst.
        analyst_firm: Firm the analyst works for.
        question: The question asked.
        answer_summary: Summary of management's answer.
        was_deflected: Whether management avoided answering directly.
    """

    analyst_name: str | None = None
    analyst_firm: str | None = None
    question: str
    answer_summary: str | None = None
    was_deflected: bool = False


class FollowUpItem(BaseModel):
    """An item to follow up on in future earnings calls.

    Attributes:
        topic: Topic to follow up on.
        context: Why this needs follow-up.
        expected_update: When an update is expected (next quarter, etc.).
    """

    topic: str
    context: str
    expected_update: str | None = None


class NotableQuote(BaseModel):
    """A notable quote from the earnings call.

    Attributes:
        speaker: Who said this.
        quote: The actual quote.
        context: Why this quote is notable.
    """

    speaker: str
    quote: str
    context: str | None = None


class TranscriptAnalysis(BaseModel):
    """LLM-generated analysis of an earnings call transcript.

    Attributes:
        transcript_id: Reference to EarningsTranscript.id.
        executive_summary: 3-5 sentence summary of the call.
        key_takeaways_bullish: List of positive signals/takeaways.
        key_takeaways_bearish: List of negative signals/concerns.
        management_tone: Overall tone of management.
        guidance_items: List of guidance given.
        guidance_overall_direction: Overall direction of guidance changes.
        warning_flags: Bearish signals to watch.
        bullish_signals: Bullish signals identified.
        analyst_questions: Summary of Q&A session.
        unanswered_questions: Questions management avoided.
        follow_up_items: Items to track in future reports.
        notable_quotes: Important quotes from the call.
        analyzed_at: When analysis was performed.
        model_used: LLM model used for analysis.

    Example:
        >>> analysis = TranscriptAnalysis(
        ...     transcript_id="nordea-earnings-2024-q3",
        ...     executive_summary="Nordea reported strong Q3 results...",
        ...     key_takeaways_bullish=["NII up 5% YoY", "Cost/income improving"],
        ...     key_takeaways_bearish=["Mortgage margin pressure"],
        ...     management_tone=ManagementTone.CONFIDENT,
        ... )
    """

    transcript_id: str

    # Summary
    executive_summary: str = ""
    key_takeaways_bullish: list[str] = Field(default_factory=list)
    key_takeaways_bearish: list[str] = Field(default_factory=list)

    # Tone
    management_tone: ManagementTone = ManagementTone.NEUTRAL

    # Guidance
    guidance_items: list[GuidanceItem] = Field(default_factory=list)
    guidance_overall_direction: GuidanceChange | None = None

    # Signals
    warning_flags: list[Signal] = Field(default_factory=list)
    bullish_signals: list[Signal] = Field(default_factory=list)

    # Q&A Analysis
    analyst_questions: list[AnalystQuestion] = Field(default_factory=list)
    unanswered_questions: list[str] = Field(default_factory=list)

    # Follow-up
    follow_up_items: list[FollowUpItem] = Field(default_factory=list)
    notable_quotes: list[NotableQuote] = Field(default_factory=list)

    # Metadata
    analyzed_at: datetime = Field(default_factory=datetime.now)
    model_used: str = "claude-sonnet-4-20250514"


class EarningsStateFile(BaseModel):
    """Schema for earnings_state.json file.

    Tracks collected transcripts and analysis status.

    Attributes:
        version: Schema version number.
        last_sync: Last sync timestamp.
        last_updated: Last update timestamp.
        transcripts: Dictionary mapping transcript_id to EarningsTranscript.
        analyzed_transcripts: List of transcript IDs that have been analyzed.
    """

    version: int = 1
    last_sync: datetime | None = None
    last_updated: datetime = Field(default_factory=datetime.now)
    transcripts: dict[str, EarningsTranscript] = Field(default_factory=dict)
    analyzed_transcripts: list[str] = Field(default_factory=list)
