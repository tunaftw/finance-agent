"""Unified models for cross-source signal aggregation."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional
import hashlib


class SignalType(str, Enum):
    """Normalized signal types across all sources."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class SignalStrength(str, Enum):
    """Signal confidence/strength."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


class AssetType(str, Enum):
    """Asset type classification."""

    STOCK = "stock"
    CRYPTO = "crypto"
    ETF = "etf"
    INDEX = "index"
    COMMODITY = "commodity"


class SourceType(str, Enum):
    """Content source type."""

    PODCAST = "podcast"
    YOUTUBE = "youtube"
    TWITTER = "twitter"


@dataclass
class Signal:
    """
    Unified signal from any source.

    Represents a bullish/bearish/neutral mention of an asset from
    podcasts, YouTube, or Twitter.
    """

    # Source identification
    source_type: SourceType
    source_id: str  # "kortochlang", "technicalroundup", "cryptodonalt"
    content_id: str  # episode/video/tweet ID
    content_date: date

    # Asset identification
    asset_symbol: str  # "BTC", "VOLVO_B", "TSLA"
    asset_name: str  # "Bitcoin", "Volvo", "Tesla"
    asset_type: AssetType

    # Signal
    signal: SignalType
    signal_strength: SignalStrength

    # Speaker
    speaker_name: str
    speaker_id: Optional[str] = None  # Linked identity

    # Context
    quote: Optional[str] = None
    reasoning: Optional[str] = None
    timestamp: Optional[str] = None  # Position in content (e.g., "10:17")

    # Metadata
    original_action: Optional[str] = None  # Original value before normalization
    price_levels: Optional[list[str]] = None

    # Entry price at signal time
    yahoo_ticker: Optional[str] = None  # Yahoo Finance ticker used
    entry_price: Optional[float] = None  # Price at content_date
    entry_price_currency: Optional[str] = None  # 'SEK', 'USD', 'DKK'

    id: Optional[str] = None

    def __post_init__(self):
        """Generate ID if not provided."""
        if self.id is None:
            self.id = self._generate_id()

    def _generate_id(self) -> str:
        """Generate unique ID from content."""
        components = [
            self.source_type.value,
            self.source_id,
            self.content_id,
            self.asset_symbol,
            self.speaker_name,
            self.timestamp or "",
        ]
        content = "|".join(components)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "source_type": self.source_type.value,
            "source_id": self.source_id,
            "content_id": self.content_id,
            "content_date": self.content_date.isoformat(),
            "asset_symbol": self.asset_symbol,
            "asset_name": self.asset_name,
            "asset_type": self.asset_type.value,
            "signal": self.signal.value,
            "signal_strength": self.signal_strength.value,
            "speaker_name": self.speaker_name,
            "speaker_id": self.speaker_id,
            "quote": self.quote,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp,
            "original_action": self.original_action,
            "price_levels": self.price_levels,
            "yahoo_ticker": self.yahoo_ticker,
            "entry_price": self.entry_price,
            "entry_price_currency": self.entry_price_currency,
        }


@dataclass
class Speaker:
    """
    Speaker identity for cross-source linking.

    Maps a person across multiple sources (podcast host + Twitter account).
    """

    id: str  # Unique identifier (slug)
    display_name: str  # "Anders Stogh"
    aliases: list[str] = field(default_factory=list)  # Alternative names

    # Source mappings
    podcast_names: list[str] = field(default_factory=list)  # Names used in podcasts
    twitter_handles: list[str] = field(default_factory=list)
    youtube_channels: list[str] = field(default_factory=list)

    def matches(self, name: str) -> bool:
        """Check if a name matches this speaker."""
        name_lower = name.lower().strip()

        # Check display name
        if self.display_name.lower() == name_lower:
            return True

        # Check aliases
        if name_lower in [a.lower() for a in self.aliases]:
            return True

        # Check podcast names
        if name_lower in [n.lower() for n in self.podcast_names]:
            return True

        return False


class SignalNormalizer:
    """
    Normalizes signals from different sources to unified format.

    Handles conversion from:
    - Podcast: buy/sell/hold/watch/avoid -> bullish/bearish/neutral
    - YouTube: bullish/bearish/neutral/mixed/long/short -> bullish/bearish/neutral
    - Twitter: buy/sell/hold -> bullish/bearish/neutral
    """

    # Podcast action mappings
    PODCAST_BULLISH = {"buy", "watch", "accumulate", "köp", "ackumulera"}
    PODCAST_BEARISH = {"sell", "avoid", "sälja", "undvik", "short"}
    PODCAST_NEUTRAL = {"hold", "håll", "neutral"}

    # YouTube sentiment mappings
    YOUTUBE_BULLISH = {"bullish", "long", "positive"}
    YOUTUBE_BEARISH = {"bearish", "short", "negative"}
    YOUTUBE_NEUTRAL = {"neutral", "mixed"}

    # Confidence mappings
    STRONG_CONFIDENCE = {"high", "strong", "hög"}
    WEAK_CONFIDENCE = {"low", "weak", "låg", "speculative"}

    @classmethod
    def normalize_podcast_action(cls, action: str) -> SignalType:
        """Convert podcast action to signal type."""
        action_lower = action.lower().strip()

        if action_lower in cls.PODCAST_BULLISH:
            return SignalType.BULLISH
        elif action_lower in cls.PODCAST_BEARISH:
            return SignalType.BEARISH
        elif action_lower in cls.PODCAST_NEUTRAL:
            return SignalType.NEUTRAL
        else:
            # Default to neutral for unknown actions
            return SignalType.NEUTRAL

    @classmethod
    def normalize_youtube_sentiment(cls, sentiment: str) -> SignalType:
        """Convert YouTube sentiment to signal type."""
        sentiment_lower = sentiment.lower().strip()

        if sentiment_lower in cls.YOUTUBE_BULLISH:
            return SignalType.BULLISH
        elif sentiment_lower in cls.YOUTUBE_BEARISH:
            return SignalType.BEARISH
        else:
            return SignalType.NEUTRAL

    @classmethod
    def normalize_confidence(cls, confidence: Optional[str]) -> SignalStrength:
        """Convert confidence to signal strength."""
        if confidence is None:
            return SignalStrength.MODERATE

        confidence_lower = confidence.lower().strip()

        if confidence_lower in cls.STRONG_CONFIDENCE:
            return SignalStrength.STRONG
        elif confidence_lower in cls.WEAK_CONFIDENCE:
            return SignalStrength.WEAK
        else:
            return SignalStrength.MODERATE

    @classmethod
    def detect_asset_type(cls, symbol: str, name: str) -> AssetType:
        """Detect asset type from symbol and name."""
        symbol_upper = symbol.upper()
        name_lower = name.lower()

        # Common crypto symbols
        crypto_symbols = {
            "BTC", "ETH", "XRP", "SOL", "DOGE", "ADA", "DOT", "AVAX",
            "LINK", "UNI", "MATIC", "ATOM", "LTC", "XLM", "ALGO",
        }

        if symbol_upper in crypto_symbols:
            return AssetType.CRYPTO

        # Check for crypto keywords in name
        crypto_keywords = {"bitcoin", "ethereum", "crypto", "coin", "token"}
        if any(kw in name_lower for kw in crypto_keywords):
            return AssetType.CRYPTO

        # Check for ETF patterns
        if symbol_upper.endswith(("-ETF", "ETF")) or "etf" in name_lower:
            return AssetType.ETF

        # Default to stock
        return AssetType.STOCK
