"""Pydantic-modeller för PodStock extraction pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


def _normalize_ticker(ticker: str | None) -> str:
    """Normalize ticker for comparison (remove exchange suffixes)."""
    if not ticker:
        return ""
    # Remove common exchange suffixes: .ST, -B, -A, .TO, etc.
    normalized = ticker.upper()
    for suffix in [".ST", ".TO", ".HK", "-B", "-A", " B", " A"]:
        normalized = normalized.replace(suffix, "")
    return normalized.strip()


def _is_ticker_like(name: str, ticker: str | None) -> bool:
    """Check if stock_name looks like a ticker (short, uppercase, matches ticker)."""
    if not name:
        return True  # Empty is "ticker-like" (bad)

    name_upper = name.upper().strip()
    ticker_normalized = _normalize_ticker(ticker)

    # Empty or whitespace-only
    if not name_upper:
        return True

    # Exact match with ticker
    if ticker_normalized and name_upper == ticker_normalized:
        return True

    # Very short all-caps (likely ticker, not company name)
    if len(name_upper) <= 5 and name_upper.isupper() and name_upper.isalpha():
        return True

    return False


# === Stock Segment Models (för djupanalys) ===


class SegmentQuote(BaseModel):
    """Ett enskilt citat från en aktiediskussion."""

    speaker: str = Field(description="Vem som sa citatet")
    text: str = Field(description="Citatets text")
    timestamp: str | None = Field(default=None, description="Tidsstämpel om tillgänglig")
    context: Literal["thesis", "bull_case", "bear_case", "metric", "conclusion", "other"] = Field(
        default="other", description="Vad citatet handlar om"
    )


class FinancialMetrics(BaseModel):
    """Finansiella nyckeltal som nämns i diskussionen."""

    pe_ratio: str | None = Field(default=None, description="P/E-tal")
    ev_ebitda: str | None = Field(default=None, description="EV/EBITDA")
    ev_sales: str | None = Field(default=None, description="EV/Sales")
    fcf_yield: str | None = Field(default=None, description="Free cash flow yield")
    dividend_yield: str | None = Field(default=None, description="Direktavkastning")
    revenue_growth: str | None = Field(default=None, description="Omsättningstillväxt")
    margin: str | None = Field(default=None, description="Marginal (brutto/EBIT/netto)")
    debt_level: str | None = Field(default=None, description="Skuldsättning")
    custom: list[str] = Field(
        default_factory=list,
        description="Branschspecifika KPIer (ARPDAU, NRR, etc.)"
    )


class ThesisComponents(BaseModel):
    """Bull/bear case och katalysatorer/risker."""

    bull_case: list[str] = Field(default_factory=list, description="Argument för att köpa")
    bear_case: list[str] = Field(default_factory=list, description="Argument emot / risker")
    catalysts: list[str] = Field(default_factory=list, description="Vad som kan driva aktien")
    risks: list[str] = Field(default_factory=list, description="Vad som kan gå fel")


class StockSegment(BaseModel):
    """Komplett segment för djupanalys av en aktiediskussion."""

    stock_name: str = Field(description="Fullständigt bolagsnamn (t.ex. 'Hacksaw Gaming', ALDRIG bara ticker)")
    ticker: str | None = Field(default=None, description="Börsticker (t.ex. 'HACSO')")

    @model_validator(mode="after")
    def validate_stock_name_not_ticker(self) -> "StockSegment":
        """Ensure stock_name is a proper company name, not a ticker."""
        if _is_ticker_like(self.stock_name, self.ticker):
            raise ValueError(
                f"stock_name måste vara fullständigt bolagsnamn, inte ticker. "
                f"Fick: stock_name='{self.stock_name}', ticker='{self.ticker}'. "
                f"Exempel: stock_name='Hacksaw Gaming', ticker='HACSO'"
            )
        return self

    # Tidsstämplar och längd
    timestamp_start: str | None = Field(default=None, description="När diskussionen börjar [HH:MM:SS]")
    timestamp_end: str | None = Field(default=None, description="När diskussionen slutar [HH:MM:SS]")
    word_count: int | None = Field(default=None, description="Antal ord i segmentet")

    # Deltagare
    speakers: list[str] = Field(default_factory=list, description="Alla som deltar i diskussionen")
    primary_speaker: str | None = Field(default=None, description="Huvudtalare")

    # Innehåll
    discussion_summary: str = Field(description="3-5 meningar som sammanfattar diskussionen")
    quotes: list[SegmentQuote] = Field(default_factory=list, description="Alla relevanta citat")

    # Analys
    financial_metrics: FinancialMetrics | None = Field(default=None)
    thesis: ThesisComponents | None = Field(default=None)

    # Positionering
    position_disclosure: Literal["owns", "bought", "sold", "none", "unknown"] = Field(
        default="unknown", description="Har talaren position i aktien?"
    )

    # Rå-data för framtida behov
    segment_text: str | None = Field(
        default=None, description="Full råtext av diskussionen (optional)"
    )


# === Insight Models (v2.1) ===


class Insight(BaseModel):
    """Investeringsvisdom extraherad från transkript."""

    quote: str = Field(description="Exakt citat som innehåller visdomen, max 300 ord")
    summary: str = Field(description="1-2 meningar som sammanfattar insikten")
    category: Literal["philosophy", "lesson", "wisdom"] = Field(
        description="philosophy=investeringsfilosofi, lesson=lärdomar, wisdom=marknadsvisdom"
    )
    speaker: str = Field(description="Vem som sa det")
    speaker_role: Literal["host", "guest", "unknown"] = Field(default="unknown")
    timestamp: str | None = Field(default=None, description="Tidsstämpel om tillgänglig")
    confidence: Literal["high", "medium", "low"] = Field(
        default="medium", description="Hur stark/tydlig insikten är"
    )
    tags: list[str] = Field(
        default_factory=list, description="Sökbara taggar: koncept, bolagsnamn, etc."
    )


class CryptoMention(BaseModel):
    """Crypto-omnämnande med sentiment."""

    asset_symbol: str = Field(description="Symbol: BTC, ETH, SOL, etc.")
    asset_name: str | None = Field(default=None, description="Fullständigt namn: Bitcoin, Ethereum")
    sentiment: Literal["bullish", "bearish", "neutral", "mixed"] = Field(
        description="Uttryckt sentiment"
    )
    speaker: str = Field(description="Vem som nämnde det")
    speaker_role: Literal["host", "guest", "unknown"] = Field(default="unknown")
    quote: str = Field(description="Stödjande citat, max 100 ord")
    context: str | None = Field(default=None, description="Diskussionskontext")
    confidence: Literal["high", "medium", "low"] = Field(default="medium")
    price_levels: list[str] = Field(
        default_factory=list, description="Prisnivåer som nämns"
    )
    timeframe: str | None = Field(
        default=None, description="'kort sikt', 'medellång sikt', 'lång sikt'"
    )


# === Existing Models ===


class StockRecommendation(BaseModel):
    """En enskild aktie-rekommendation från ett poddavsnitt."""

    stock_name: str = Field(description="Fullständigt bolagsnamn (t.ex. 'Evolution Gaming', ALDRIG bara ticker)")
    ticker: str | None = Field(default=None, description="Börsticker (t.ex. 'EVO')")
    action: Literal["buy", "sell", "hold", "watch", "avoid"] = Field(
        description="Typ av rekommendation"
    )

    @model_validator(mode="after")
    def validate_stock_name_not_ticker(self) -> "StockRecommendation":
        """Ensure stock_name is a proper company name, not a ticker."""
        if _is_ticker_like(self.stock_name, self.ticker):
            raise ValueError(
                f"stock_name måste vara fullständigt bolagsnamn, inte ticker. "
                f"Fick: stock_name='{self.stock_name}', ticker='{self.ticker}'. "
                f"Exempel: stock_name='Evolution Gaming', ticker='EVO'"
            )
        return self
    confidence: Literal["high", "medium", "low", "speculative"] = Field(
        description="Hur övertygad är talaren"
    )
    speaker: str | None = Field(default=None, description="Vem gav rekommendationen")
    speaker_role: Literal["host", "guest", "unknown"] = Field(default="unknown")
    timestamp: str | None = Field(
        default=None, description="Tidsstämpel [HH:MM:SS] om tillgänglig"
    )

    reasoning: str = Field(description="Sammanfattning av argumentet, 1-3 meningar")
    price_target: str | None = Field(default=None, description="Kursmål om nämnt")
    time_horizon: str | None = Field(
        default=None, description="'kort sikt', 'lång sikt', '6 månader'"
    )

    quote: str = Field(description="Exakt citat från transkriptet, max 100 ord")

    # Kategorisering
    sector: str | None = Field(
        default=None, description="Bransch: 'tech', 'fastigheter', 'finans', etc."
    )
    market: Literal["sweden", "us", "europe", "other", "unknown"] = Field(
        default="unknown"
    )

    # Extra alfa-fält (v2.1) - optional, fylls bara i om det nämns explicit
    position_context: str | None = Field(
        default=None,
        description="Fri text om positionsstorlek, t.ex. '50% av portföljen', 'största positionen'"
    )
    downside_note: str | None = Field(
        default=None,
        description="Fri text om downside/risk, t.ex. '30% neddida', 'värsta fall 50 SEK'"
    )
    catalyst_timing: str | None = Field(
        default=None,
        description="Katalysator med timing, t.ex. 'Rapport 15 feb', 'produktlansering Q2'"
    )


class EpisodeAnalysis(BaseModel):
    """Komplett analys av ett poddavsnitt."""

    # Schema version för bakåtkompatibilitet
    schema_version: str = Field(default="2.1", description="1.0=legacy, 2.0=stock_segments, 2.1=insights+crypto")

    # Identifiering
    episode_id: str = Field(description="Unikt ID, t.ex. 'borspodden_2024-12-20'")
    podcast_name: str = Field(description="Podcastens namn")
    episode_title: str | None = Field(default=None)
    episode_number: int | None = Field(default=None)
    date: str = Field(description="Publiceringsdatum, ISO-format YYYY-MM-DD")

    # Deltagare
    hosts: list[str] = Field(default_factory=list)
    guests: list[str] = Field(default_factory=list)

    # Innehåll
    main_topics: list[str] = Field(description="Max 5 huvudämnen som diskuteras")
    stocks_discussed: list[str] = Field(description="Alla aktier/bolag som nämns")
    recommendations: list[StockRecommendation] = Field(default_factory=list)

    # Djupanalys (v2.0) - optional för bakåtkompatibilitet
    stock_segments: list[StockSegment] = Field(
        default_factory=list,
        description="Detaljerade segment för aktier med >2 min diskussion"
    )

    # Insights och Crypto (v2.1)
    insights: list[Insight] = Field(
        default_factory=list,
        description="Investeringsvisdom och lärdomar extraherade från transkriptet"
    )
    crypto_mentions: list[CryptoMention] = Field(
        default_factory=list,
        description="Cryptocurrency-omnämnanden med sentiment"
    )

    # Sentiment
    market_sentiment: Literal["bullish", "bearish", "neutral", "mixed"] = Field(
        description="Övergripande marknadssyn i avsnittet"
    )

    # Sammanfattning
    summary: str = Field(description="3-5 meningar som sammanfattar avsnittet")
    key_takeaways: list[str] = Field(description="3-5 huvudpunkter för investerare")

    # Metadata
    transcript_file: str
    transcript_word_count: int
    has_timestamps: bool = Field(default=False)
    processed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    model_used: str = Field(default="claude-sonnet-4-20250514")


class ProcessingStatus(BaseModel):
    """Håller koll på processing-status."""

    file_path: str
    status: Literal["pending", "processing", "completed", "error"]
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None
    retry_count: int = 0
