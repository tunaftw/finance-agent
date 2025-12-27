"""Crypto sentiment analyzer using LLM.

This module provides LLM-based extraction of crypto sentiment
from transcripts, using the existing LLM client infrastructure.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import re

from podstock.analysis import extract_json_from_response
from podstock.crypto.models import (
    CryptoMention,
    CryptoSentimentAnalysis,
    PricePrediction,
    SentimentLevel,
)
from podstock.crypto.prompt_templates import (
    CRYPTO_EXTRACTION_SYSTEM_PROMPT,
    CRYPTO_EXTRACTION_USER_PROMPT,
    CRYPTO_FEW_SHOT_EXAMPLE,
)
from podstock.extract.llm_client import LLMClient


class CryptoAnalyzer:
    """Analyzes transcripts for crypto sentiment using LLM.

    Uses the same LLM client infrastructure as the stock extraction
    but with crypto-specific prompts and models.

    Example:
        >>> from podstock.extract.llm_client import ClaudeClient
        >>> client = ClaudeClient()
        >>> analyzer = CryptoAnalyzer(client)
        >>> analysis = analyzer.analyze_transcript(
        ...     transcript_path=Path("data/youtube/transcripts/tr/abc123.txt"),
        ...     source_type="youtube",
        ...     channel_name="Technical Roundup",
        ... )
    """

    def __init__(
        self,
        llm_client: LLMClient,
        max_tokens: int = 8000,
    ) -> None:
        """Initialize the analyzer.

        Args:
            llm_client: LLM client to use for analysis.
            max_tokens: Maximum tokens for response.
        """
        self.llm_client = llm_client
        self.max_tokens = max_tokens

    def analyze_transcript(
        self,
        transcript_path: Path,
        source_id: str,
        source_type: str,
        channel_name: str,
        date: str | None = None,
        title: str | None = None,
    ) -> CryptoSentimentAnalysis:
        """Analyze a transcript for crypto sentiment.

        Args:
            transcript_path: Path to transcript file.
            source_id: ID of the source (video ID, episode ID).
            source_type: Type of source (youtube, podcast, twitter).
            channel_name: Name of channel/podcast.
            date: Publication date (YYYY-MM-DD format).
            title: Title of the content.

        Returns:
            CryptoSentimentAnalysis with extracted sentiment.
        """
        # Read transcript
        transcript_content = transcript_path.read_text(encoding="utf-8")

        # Skip header if present
        if transcript_content.startswith("="):
            parts = transcript_content.split("=" * 60)
            if len(parts) >= 3:
                transcript_content = parts[2].strip()

        # Extract date from filename if not provided
        if not date:
            date = self._extract_date_from_path(transcript_path)

        # Build prompt
        user_prompt = CRYPTO_EXTRACTION_USER_PROMPT.format(
            source_id=source_id,
            source_type=source_type,
            channel_name=channel_name,
            date=date,
            title=title or "Unknown",
            transcript=transcript_content[:100000],  # Limit size
        )

        # Include few-shot example in system prompt
        system_prompt = (
            CRYPTO_EXTRACTION_SYSTEM_PROMPT
            + "\n\n"
            + CRYPTO_FEW_SHOT_EXAMPLE
        )

        # Call LLM
        response = self.llm_client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=self.max_tokens,
        )

        # Parse response
        analysis = self._parse_response(
            response,
            source_id=source_id,
            source_type=source_type,
            channel_name=channel_name,
            date=date,
            title=title,
            word_count=len(transcript_content.split()),
        )

        return analysis

    def analyze_text(
        self,
        text: str,
        source_id: str,
        source_type: str,
        channel_name: str,
        date: str,
        title: str | None = None,
    ) -> CryptoSentimentAnalysis:
        """Analyze raw text for crypto sentiment.

        Args:
            text: Transcript text content.
            source_id: Source ID.
            source_type: Source type.
            channel_name: Channel/podcast name.
            date: Publication date.
            title: Content title.

        Returns:
            CryptoSentimentAnalysis with extracted sentiment.
        """
        user_prompt = CRYPTO_EXTRACTION_USER_PROMPT.format(
            source_id=source_id,
            source_type=source_type,
            channel_name=channel_name,
            date=date,
            title=title or "Unknown",
            transcript=text[:100000],
        )

        system_prompt = (
            CRYPTO_EXTRACTION_SYSTEM_PROMPT
            + "\n\n"
            + CRYPTO_FEW_SHOT_EXAMPLE
        )

        response = self.llm_client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=self.max_tokens,
        )

        return self._parse_response(
            response,
            source_id=source_id,
            source_type=source_type,
            channel_name=channel_name,
            date=date,
            title=title,
            word_count=len(text.split()),
        )

    def _parse_response(
        self,
        response: str,
        source_id: str,
        source_type: str,
        channel_name: str,
        date: str,
        title: str | None,
        word_count: int,
    ) -> CryptoSentimentAnalysis:
        """Parse LLM response into CryptoSentimentAnalysis.

        Args:
            response: Raw LLM response.
            source_id: Source ID.
            source_type: Source type.
            channel_name: Channel name.
            date: Date string.
            title: Title.
            word_count: Transcript word count.

        Returns:
            Parsed analysis object.
        """
        # Extract JSON from response
        json_str = extract_json_from_response(response)
        data = json.loads(json_str)

        # Parse mentions
        mentions = []
        for m in data.get("mentions", []):
            try:
                mention = CryptoMention(
                    asset_name=m.get("asset_name", "Unknown"),
                    asset_symbol=m.get("asset_symbol", "UNKNOWN"),
                    asset_type=m.get("asset_type", "coin"),
                    sentiment=self._parse_sentiment(m.get("sentiment", "neutral")),
                    confidence=m.get("confidence", "medium"),
                    speaker=m.get("speaker"),
                    timestamp=m.get("timestamp"),
                    quote=m.get("quote", "No quote provided"),
                    reasoning=m.get("reasoning", "No reasoning provided"),
                    price_prediction=m.get("price_prediction"),
                    price_target=m.get("price_target"),
                    price_target_currency=m.get("price_target_currency", "USD"),
                    time_horizon=m.get("time_horizon"),
                    market_cap_awareness=m.get("market_cap_awareness", False),
                    mentioned_catalysts=m.get("mentioned_catalysts", []),
                    risk_factors_mentioned=m.get("risk_factors_mentioned", []),
                )
                mentions.append(mention)
            except Exception:
                continue  # Skip malformed mentions

        # Parse overall sentiment
        overall_sentiment = self._parse_sentiment(
            data.get("overall_market_sentiment", "neutral")
        )

        # Parse bitcoin dominance view
        btc_dom = data.get("bitcoin_dominance_view", "not_discussed")
        if btc_dom not in ["increasing", "decreasing", "stable", "not_discussed"]:
            btc_dom = "not_discussed"

        # Create analysis object
        analysis = CryptoSentimentAnalysis(
            source_id=source_id,
            source_type=source_type,
            channel_or_podcast=channel_name,
            title=title,
            date=date,
            speakers=data.get("speakers", []),
            main_topics=data.get("main_topics", [])[:5],
            assets_discussed=data.get("assets_discussed", []),
            mentions=mentions,
            overall_market_sentiment=overall_sentiment,
            bitcoin_dominance_view=btc_dom,
            alt_season_prediction=data.get("alt_season_prediction"),
            summary=data.get("summary", ""),
            key_takeaways=data.get("key_takeaways", [])[:5],
            transcript_word_count=word_count,
            has_timestamps=bool(data.get("mentions") and any(
                m.get("timestamp") for m in data.get("mentions", [])
            )),
            model_used=getattr(self.llm_client, "model_name", "unknown"),
        )

        return analysis

    def _parse_sentiment(self, sentiment: str) -> SentimentLevel:
        """Parse sentiment string to SentimentLevel enum.

        Args:
            sentiment: Sentiment string from LLM.

        Returns:
            SentimentLevel enum value.
        """
        sentiment = sentiment.lower().replace(" ", "_")

        sentiment_map = {
            "very_bullish": SentimentLevel.VERY_BULLISH,
            "bullish": SentimentLevel.BULLISH,
            "neutral": SentimentLevel.NEUTRAL,
            "bearish": SentimentLevel.BEARISH,
            "very_bearish": SentimentLevel.VERY_BEARISH,
            # Alternative spellings
            "extremely_bullish": SentimentLevel.VERY_BULLISH,
            "extremely_bearish": SentimentLevel.VERY_BEARISH,
            "slightly_bullish": SentimentLevel.BULLISH,
            "slightly_bearish": SentimentLevel.BEARISH,
        }

        return sentiment_map.get(sentiment, SentimentLevel.NEUTRAL)

    def _extract_date_from_path(self, path: Path) -> str:
        """Try to extract date from file path.

        Args:
            path: File path.

        Returns:
            Date string (YYYY-MM-DD) or today's date.
        """
        # Try to find date pattern in path
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", str(path))
        if date_match:
            return date_match.group(1)

        return datetime.now().strftime("%Y-%m-%d")

    def extract_predictions(
        self,
        analysis: CryptoSentimentAnalysis,
        source_name: str,
    ) -> list[PricePrediction]:
        """Extract verifiable predictions from analysis.

        Args:
            analysis: Completed sentiment analysis.
            source_name: Name of the source.

        Returns:
            List of PricePrediction objects.
        """
        predictions = []

        for mention in analysis.mentions:
            # Only create prediction if there's a price target or clear direction
            if not mention.price_target and not mention.time_horizon:
                continue

            # Determine direction from sentiment
            if mention.sentiment in [SentimentLevel.BULLISH, SentimentLevel.VERY_BULLISH]:
                direction = "up"
            elif mention.sentiment in [SentimentLevel.BEARISH, SentimentLevel.VERY_BEARISH]:
                direction = "down"
            else:
                direction = "sideways"

            # Parse deadline from time horizon
            deadline = self._parse_deadline(mention.time_horizon)

            prediction = PricePrediction(
                prediction_id=f"{analysis.source_id}_{mention.asset_symbol}_{datetime.now().timestamp():.0f}",
                source_id=analysis.source_id,
                source_type=analysis.source_type,
                source_name=source_name,
                asset_symbol=mention.asset_symbol,
                predicted_at=datetime.now(),
                prediction_text=mention.quote,
                target_price=mention.price_target,
                target_currency=mention.price_target_currency,
                direction=direction,
                time_horizon=mention.time_horizon,
                deadline=deadline,
                price_at_prediction=0.0,  # Will be filled by price tracker
                speaker=mention.speaker,
            )

            predictions.append(prediction)

        return predictions

    def _parse_deadline(self, time_horizon: str | None) -> datetime | None:
        """Parse time horizon string into deadline datetime.

        Args:
            time_horizon: Time horizon string like "end of 2025", "Q1 2025", etc.

        Returns:
            Datetime for deadline or None.
        """
        if not time_horizon:
            return None

        horizon_lower = time_horizon.lower()
        now = datetime.now()

        # Handle specific patterns
        if "end of 2025" in horizon_lower or "eoy 2025" in horizon_lower:
            return datetime(2025, 12, 31)
        if "end of 2026" in horizon_lower or "eoy 2026" in horizon_lower:
            return datetime(2026, 12, 31)
        if "q1 2025" in horizon_lower:
            return datetime(2025, 3, 31)
        if "q2 2025" in horizon_lower:
            return datetime(2025, 6, 30)
        if "q3 2025" in horizon_lower:
            return datetime(2025, 9, 30)
        if "q4 2025" in horizon_lower:
            return datetime(2025, 12, 31)
        if "1 week" in horizon_lower or "one week" in horizon_lower:
            from datetime import timedelta
            return now + timedelta(weeks=1)
        if "1 month" in horizon_lower or "one month" in horizon_lower:
            from datetime import timedelta
            return now + timedelta(days=30)
        if "3 month" in horizon_lower or "three month" in horizon_lower:
            from datetime import timedelta
            return now + timedelta(days=90)
        if "6 month" in horizon_lower or "six month" in horizon_lower:
            from datetime import timedelta
            return now + timedelta(days=180)
        if "1 year" in horizon_lower or "one year" in horizon_lower:
            from datetime import timedelta
            return now + timedelta(days=365)

        return None


