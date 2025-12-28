"""SQLAlchemy ORM models for PodStock database."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Source(Base):
    """Content source (podcast, twitter account, youtube channel)."""

    __tablename__ = "sources"

    id = Column(Text, primary_key=True)  # 'fillorkill', 'vildkatten'
    type = Column(Text, nullable=False)  # 'podcast', 'twitter', 'youtube'
    name = Column(Text, nullable=False)  # 'Fill or Kill'
    description = Column(Text)
    language = Column(Text, default="sv")
    extra_data = Column(Text)  # JSON metadata
    active = Column(Integer, default=1)
    trust_rating = Column(Integer, default=3)  # 1-5 scale for source credibility
    trust_notes = Column(Text)  # Free text explaining trust rating
    created_at = Column(Text, default=lambda: datetime.now().isoformat())
    updated_at = Column(Text, default=lambda: datetime.now().isoformat())

    # Relationships
    content = relationship("Content", back_populates="source", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Source(id={self.id!r}, name={self.name!r}, type={self.type!r})>"


class Content(Base):
    """Content item (episode, tweet, video)."""

    __tablename__ = "content"

    id = Column(Text, primary_key=True)  # 'fillorkill-2025-12-23-cf58'
    source_id = Column(Text, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    type = Column(Text, nullable=False)  # 'episode', 'tweet', 'video'
    external_id = Column(Text)  # tweet_id, video_id, guid
    title = Column(Text)
    published_at = Column(Text, nullable=False)
    raw_text = Column(Text)
    word_count = Column(Integer)
    duration_seconds = Column(Integer)
    extra_data = Column(Text)  # JSON metadata
    created_at = Column(Text, default=lambda: datetime.now().isoformat())

    # Relationships
    source = relationship("Source", back_populates="content")
    analyses = relationship("Analysis", back_populates="content", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Content(id={self.id!r}, title={self.title!r})>"


class Analysis(Base):
    """Versioned analysis of content."""

    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content_id = Column(Text, ForeignKey("content.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    content_hash = Column(Text)  # SHA256 for idempotency
    model_used = Column(Text)
    analyzed_at = Column(Text, nullable=False)
    summary = Column(Text)
    sentiment = Column(Text)  # 'bullish', 'bearish', 'neutral'
    raw_json = Column(Text)
    created_at = Column(Text, default=lambda: datetime.now().isoformat())

    __table_args__ = (UniqueConstraint("content_id", "version", name="uq_analysis_version"),)

    # Relationships
    content = relationship("Content", back_populates="analyses")
    recommendations = relationship(
        "Recommendation", back_populates="analysis", cascade="all, delete-orphan"
    )
    mentions = relationship("Mention", back_populates="analysis", cascade="all, delete-orphan")
    key_takeaways = relationship(
        "KeyTakeaway", back_populates="analysis", cascade="all, delete-orphan"
    )
    load_logs = relationship("LoadLog", back_populates="analysis")

    def __repr__(self) -> str:
        return f"<Analysis(id={self.id}, content_id={self.content_id!r}, version={self.version})>"


class Security(Base):
    """Security/stock."""

    __tablename__ = "securities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(Text, nullable=False)  # 'EVO.ST', 'AAPL'
    name = Column(Text, nullable=False)  # 'Evolution', 'Apple'
    exchange = Column(Text)  # 'OMX', 'NYSE', 'LSE'
    market = Column(Text)  # 'sweden', 'usa', 'europe'
    currency = Column(Text)  # 'SEK', 'USD'
    isin = Column(Text)
    sector = Column(Text)
    asset_type = Column(Text, default="stock")  # 'stock', 'crypto'
    status = Column(Text, default="active")  # 'active', 'delisted'
    delisted_date = Column(Text)
    created_at = Column(Text, default=lambda: datetime.now().isoformat())

    __table_args__ = (UniqueConstraint("ticker", "exchange", name="uq_security_ticker_exchange"),)

    # Relationships
    aliases = relationship("SecurityAlias", back_populates="security", cascade="all, delete-orphan")
    primary_relations = relationship(
        "SecurityRelation",
        foreign_keys="SecurityRelation.primary_id",
        back_populates="primary",
        cascade="all, delete-orphan",
    )
    related_relations = relationship(
        "SecurityRelation",
        foreign_keys="SecurityRelation.related_id",
        back_populates="related",
        cascade="all, delete-orphan",
    )
    recommendations = relationship("Recommendation", back_populates="security")
    mentions = relationship("Mention", back_populates="security")
    prices = relationship("Price", back_populates="security", cascade="all, delete-orphan")
    pending_resolutions = relationship("PendingSecurity", back_populates="resolved_security")

    def __repr__(self) -> str:
        return f"<Security(id={self.id}, ticker={self.ticker!r}, name={self.name!r})>"


class SecurityAlias(Base):
    """Alternative names for security lookup."""

    __tablename__ = "security_aliases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    security_id = Column(Integer, ForeignKey("securities.id", ondelete="CASCADE"), nullable=False)
    alias = Column(Text, nullable=False, unique=True)
    alias_type = Column(Text, default="name")  # 'name', 'ticker_variant', 'twitter'

    # Relationships
    security = relationship("Security", back_populates="aliases")

    def __repr__(self) -> str:
        return f"<SecurityAlias(alias={self.alias!r}, security_id={self.security_id})>"


class SecurityRelation(Base):
    """Relations between securities (same company on different exchanges)."""

    __tablename__ = "security_relations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    primary_id = Column(Integer, ForeignKey("securities.id"), nullable=False)
    related_id = Column(Integer, ForeignKey("securities.id"), nullable=False)
    relation_type = Column(Text)  # 'same_company', 'adr', 'dual_listing'

    __table_args__ = (UniqueConstraint("primary_id", "related_id", name="uq_security_relation"),)

    # Relationships
    primary = relationship("Security", foreign_keys=[primary_id], back_populates="primary_relations")
    related = relationship("Security", foreign_keys=[related_id], back_populates="related_relations")

    def __repr__(self) -> str:
        return f"<SecurityRelation(primary={self.primary_id}, related={self.related_id})>"


class PendingSecurity(Base):
    """Unmatched securities for manual review."""

    __tablename__ = "pending_securities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_name = Column(Text, nullable=False)
    raw_ticker = Column(Text)
    source = Column(Text)
    context = Column(Text)
    occurrence_count = Column(Integer, default=1)
    status = Column(Text, default="pending")  # 'pending', 'resolved', 'rejected'
    resolved_security_id = Column(Integer, ForeignKey("securities.id"))
    created_at = Column(Text, default=lambda: datetime.now().isoformat())

    __table_args__ = (UniqueConstraint("raw_name", "raw_ticker", name="uq_pending_security"),)

    # Relationships
    resolved_security = relationship("Security", back_populates="pending_resolutions")

    def __repr__(self) -> str:
        return f"<PendingSecurity(raw_name={self.raw_name!r}, status={self.status!r})>"


class Recommendation(Base):
    """Stock recommendation (buy/sell signal)."""

    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    security_id = Column(Integer, ForeignKey("securities.id", ondelete="SET NULL"))
    raw_stock_name = Column(Text, nullable=False)
    raw_ticker = Column(Text)
    action = Column(Text, nullable=False)  # 'buy', 'sell', 'hold', 'watch', 'avoid'
    confidence = Column(Text)  # 'high', 'medium', 'low'
    speaker = Column(Text)
    speaker_role = Column(Text)
    reasoning = Column(Text)
    quote = Column(Text)
    timestamp = Column(Text)
    price_target = Column(Text)
    time_horizon = Column(Text)
    sector = Column(Text)
    market = Column(Text)
    created_at = Column(Text, default=lambda: datetime.now().isoformat())

    # Relationships
    analysis = relationship("Analysis", back_populates="recommendations")
    security = relationship("Security", back_populates="recommendations")
    performance = relationship(
        "RecommendationPerformance",
        back_populates="recommendation",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Recommendation(id={self.id}, stock={self.raw_stock_name!r}, action={self.action!r})>"


class Mention(Base):
    """Stock mention (without clear signal)."""

    __tablename__ = "mentions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    security_id = Column(Integer, ForeignKey("securities.id", ondelete="SET NULL"))
    raw_stock_name = Column(Text, nullable=False)
    raw_ticker = Column(Text)
    sentiment = Column(Text)  # 'positive', 'negative', 'neutral'
    context = Column(Text)
    created_at = Column(Text, default=lambda: datetime.now().isoformat())

    # Relationships
    analysis = relationship("Analysis", back_populates="mentions")
    security = relationship("Security", back_populates="mentions")

    def __repr__(self) -> str:
        return f"<Mention(id={self.id}, stock={self.raw_stock_name!r})>"


class KeyTakeaway(Base):
    """Key takeaway from analysis."""

    __tablename__ = "key_takeaways"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    takeaway = Column(Text, nullable=False)
    sort_order = Column(Integer, default=0)

    # Relationships
    analysis = relationship("Analysis", back_populates="key_takeaways")

    def __repr__(self) -> str:
        return f"<KeyTakeaway(id={self.id}, takeaway={self.takeaway[:50]!r}...)>"


class Price(Base):
    """Historical price data."""

    __tablename__ = "prices"

    security_id = Column(Integer, ForeignKey("securities.id"), primary_key=True)
    date = Column(Text, primary_key=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float, nullable=False)
    adj_close = Column(Float)
    volume = Column(Integer)
    source = Column(Text)
    created_at = Column(Text, default=lambda: datetime.now().isoformat())

    # Relationships
    security = relationship("Security", back_populates="prices")

    def __repr__(self) -> str:
        return f"<Price(security_id={self.security_id}, date={self.date!r}, close={self.close})>"


class RecommendationPerformance(Base):
    """Performance tracking for recommendations."""

    __tablename__ = "recommendation_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(
        Integer, ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    price_at_rec = Column(Float)
    price_1d = Column(Float)
    price_7d = Column(Float)
    price_30d = Column(Float)
    price_90d = Column(Float)
    price_365d = Column(Float)
    return_1d = Column(Float)
    return_7d = Column(Float)
    return_30d = Column(Float)
    return_90d = Column(Float)
    return_365d = Column(Float)
    calculated_at = Column(Text)
    is_complete = Column(Integer, default=0)

    # Relationships
    recommendation = relationship("Recommendation", back_populates="performance")

    def __repr__(self) -> str:
        return f"<RecommendationPerformance(recommendation_id={self.recommendation_id})>"


class LoadLog(Base):
    """Track loaded files for idempotency."""

    __tablename__ = "load_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(Text, nullable=False)
    file_hash = Column(Text, nullable=False)
    file_type = Column(Text)  # 'podcast', 'twitter'
    loaded_at = Column(Text, default=lambda: datetime.now().isoformat())
    analysis_id = Column(Integer, ForeignKey("analyses.id"))
    status = Column(Text, default="success")  # 'success', 'failed', 'skipped'
    error_message = Column(Text)

    __table_args__ = (UniqueConstraint("file_path", "file_hash", name="uq_load_log"),)

    # Relationships
    analysis = relationship("Analysis", back_populates="load_logs")

    def __repr__(self) -> str:
        return f"<LoadLog(file_path={self.file_path!r}, status={self.status!r})>"


# =============================================================================
# Unified Signal Layer
# =============================================================================


class SpeakerIdentity(Base):
    """Speaker identity for cross-source linking."""

    __tablename__ = "speaker_identities"

    id = Column(Text, primary_key=True)  # Slug: 'anders-stogh'
    display_name = Column(Text, nullable=False)  # 'Anders Stogh'
    aliases = Column(Text)  # JSON array of alternative names
    podcast_names = Column(Text)  # JSON array of podcast display names
    twitter_handles = Column(Text)  # JSON array of Twitter handles
    youtube_channels = Column(Text)  # JSON array of YouTube channels
    created_at = Column(Text, default=lambda: datetime.now().isoformat())
    updated_at = Column(Text, default=lambda: datetime.now().isoformat())

    # Relationships
    signals = relationship("UnifiedSignal", back_populates="speaker")

    def __repr__(self) -> str:
        return f"<SpeakerIdentity(id={self.id!r}, name={self.display_name!r})>"


class UnifiedSignal(Base):
    """
    Unified signal from any source.

    Aggregates bullish/bearish/neutral signals from podcasts, YouTube, and Twitter
    into a single queryable table.
    """

    __tablename__ = "unified_signals"

    id = Column(Text, primary_key=True)  # SHA256 hash of content
    source_type = Column(Text, nullable=False)  # 'podcast', 'youtube', 'twitter'
    source_id = Column(Text, nullable=False)  # 'kortochlang', 'technicalroundup'
    content_id = Column(Text, nullable=False)  # Episode/video/tweet ID
    content_date = Column(Text, nullable=False)  # ISO date

    # Asset
    asset_symbol = Column(Text, nullable=False)  # 'BTC', 'VOLVO_B'
    asset_name = Column(Text, nullable=False)  # 'Bitcoin', 'Volvo'
    asset_type = Column(Text, nullable=False)  # 'crypto', 'stock'

    # Signal
    signal = Column(Text, nullable=False)  # 'bullish', 'bearish', 'neutral'
    signal_strength = Column(Text, nullable=False)  # 'strong', 'moderate', 'weak'
    original_action = Column(Text)  # Original value before normalization

    # Speaker
    speaker_name = Column(Text, nullable=False)
    speaker_id = Column(Text, ForeignKey("speaker_identities.id"))

    # Context
    quote = Column(Text)
    reasoning = Column(Text)
    timestamp = Column(Text)  # Position in content
    price_levels = Column(Text)  # JSON array

    # Entry price at signal time
    yahoo_ticker = Column(Text)  # Yahoo Finance ticker used
    entry_price = Column(Float)  # Price at content_date
    entry_price_currency = Column(Text)  # 'SEK', 'USD', 'DKK'

    # Metadata
    created_at = Column(Text, default=lambda: datetime.now().isoformat())

    __table_args__ = (
        Index("ix_unified_signals_content_date", "content_date"),
        Index("ix_unified_signals_asset_symbol", "asset_symbol"),
        Index("ix_unified_signals_speaker_name", "speaker_name"),
        Index("ix_unified_signals_signal", "signal"),
        Index("ix_unified_signals_source_type", "source_type"),
    )

    # Relationships
    speaker = relationship("SpeakerIdentity", back_populates="signals")

    def __repr__(self) -> str:
        return f"<UnifiedSignal(id={self.id!r}, asset={self.asset_symbol!r}, signal={self.signal!r})>"
