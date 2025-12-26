"""Pydantic-modeller för PodStock extraction pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class StockRecommendation(BaseModel):
    """En enskild aktie-rekommendation från ett poddavsnitt."""

    stock_name: str = Field(description="Aktiens namn, t.ex. 'Evolution'")
    ticker: str | None = Field(default=None, description="Ticker om nämnt, t.ex. 'EVO'")
    action: Literal["buy", "sell", "hold", "watch", "avoid"] = Field(
        description="Typ av rekommendation"
    )
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


class EpisodeAnalysis(BaseModel):
    """Komplett analys av ett poddavsnitt."""

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
