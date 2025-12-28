"""Tweet analysis using LLM for extracting stock recommendations.

This module processes tweets through Claude to identify buy/sell/hold signals
and extract investment-related insights.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from podstock.analysis import extract_json_from_response
from podstock.extract.llm_client import LLMClient, create_llm_client
from podstock.twitter.models import (
    StockMention,
    Tweet,
    TweetActionType,
    TweetAnalysis,
)
from podstock.twitter.storage import TweetStorage


TWEET_ANALYSIS_SYSTEM_PROMPT = """Du är en expert på att analysera investeringsrelaterade tweets från svenska finansprofiler.

Din uppgift är att identifiera:
1. Konkreta aktierekommendationer (köp/sälj/hold/watch/avoid)
2. Confidence level baserat på hur explicit rekommendationen är
3. Marknadssentiment (bullish/bearish/neutral/mixed)

VIKTIGA RIKTLINJER:
- Var KONSERVATIV: Bara tydliga rekommendationer = high confidence
- "Intressant bolag" eller "tittar på" = watch, INTE buy
- Faktiska köp/sälj ("köpte idag", "sålde av") = high confidence
- Diskussion utan rekommendation = unknown action
- Om tweeten bara nämner en ticker utan åsikt = neutral sentiment, unknown action

Returnera ALLTID valid JSON enligt detta schema:
{
  "stock_mentions": [
    {
      "stock_name": "Bolagsnamn",
      "ticker": "TICKER",
      "action": "buy|sell|hold|watch|avoid|unknown",
      "confidence": "high|medium|low|speculative",
      "reasoning": "Kort motivering",
      "quote": "Relevant del av tweeten"
    }
  ],
  "market_sentiment": "bullish|bearish|neutral|mixed",
  "is_actionable": true/false,
  "is_speculation": true/false,
  "has_price_target": true/false
}"""

TWEET_ANALYSIS_USER_PROMPT = """Analysera denna tweet från @{author}:

---
{tweet_text}
---

Tickers som nämns: {tickers}
Datum: {posted_at}

Returnera din analys som JSON."""


class TweetAnalyzer:
    """Analyzes tweets using LLM to extract stock recommendations.

    Example:
        >>> analyzer = TweetAnalyzer()
        >>> analysis = analyzer.analyze_tweet(tweet)
        >>> print(analysis.stock_mentions)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        """Initialize the analyzer.

        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
            model: Model to use for analysis.
        """
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key and not model.startswith("ollama:"):
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable."
            )

        self.client = create_llm_client(model, api_key)
        self.model = model

    def analyze_tweet(self, tweet: Tweet) -> TweetAnalysis | None:
        """Analyze a single tweet for stock recommendations.

        Args:
            tweet: Tweet to analyze.

        Returns:
            TweetAnalysis if successful, None if analysis fails.
        """
        # Ensure entities are extracted
        if not tweet.mentioned_tickers:
            tweet.extract_entities()

        # Build prompt
        user_prompt = TWEET_ANALYSIS_USER_PROMPT.format(
            author=tweet.author_handle,
            tweet_text=tweet.text,
            tickers=", ".join(f"${t}" for t in tweet.mentioned_tickers) or "Inga",
            posted_at=tweet.posted_at.strftime("%Y-%m-%d"),
        )

        try:
            response = self.client.generate(
                system_prompt=TWEET_ANALYSIS_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=1500,
            )

            # Extract JSON from response
            json_str = extract_json_from_response(response)
            data = json.loads(json_str)

            # Parse stock mentions
            stock_mentions = []
            for mention in data.get("stock_mentions", []):
                action_str = mention.get("action", "unknown").lower()
                try:
                    action = TweetActionType(action_str)
                except ValueError:
                    action = TweetActionType.UNKNOWN

                stock_mentions.append(
                    StockMention(
                        stock_name=mention.get("stock_name", "Unknown"),
                        ticker=mention.get("ticker"),
                        action=action,
                        confidence=mention.get("confidence", "low"),
                        reasoning=mention.get("reasoning"),
                        quote=mention.get("quote", tweet.text[:100]),
                    )
                )

            return TweetAnalysis(
                tweet_id=tweet.id,
                source_id=tweet.source_id,
                stock_mentions=stock_mentions,
                market_sentiment=data.get("market_sentiment"),
                is_actionable=data.get("is_actionable", False),
                is_speculation=data.get("is_speculation", False),
                has_price_target=data.get("has_price_target", False),
                model_used=self.client.model_name,
            )

        except (json.JSONDecodeError, KeyError) as e:
            print(f"  Failed to parse response for tweet {tweet.id}: {e}")
            return None

    def analyze_tweets(
        self,
        tweets: list[Tweet],
        filter_with_tickers: bool = True,
        progress_callback: callable | None = None,
    ) -> list[TweetAnalysis]:
        """Analyze multiple tweets.

        Args:
            tweets: List of tweets to analyze.
            filter_with_tickers: Only analyze tweets that mention tickers.
            progress_callback: Optional callback for progress updates.

        Returns:
            List of TweetAnalysis objects.
        """
        # Filter to tweets with tickers if requested
        if filter_with_tickers:
            to_analyze = []
            for tweet in tweets:
                if not tweet.mentioned_tickers:
                    tweet.extract_entities()
                if tweet.mentioned_tickers:
                    to_analyze.append(tweet)
        else:
            to_analyze = tweets

        analyses = []
        for i, tweet in enumerate(to_analyze, 1):
            if progress_callback:
                progress_callback(f"Analyzing {i}/{len(to_analyze)}: {tweet.id}")

            analysis = self.analyze_tweet(tweet)
            if analysis:
                analyses.append(analysis)

        return analyses

    def save_analyses(
        self,
        analyses: list[TweetAnalysis],
        output_dir: Path,
        source_id: str,
    ) -> Path:
        """Save analyses to JSON file.

        Args:
            analyses: List of analyses to save.
            output_dir: Directory to save to.
            source_id: Source identifier for filename.

        Returns:
            Path to saved file.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{source_id}-tweet-analyses.json"
        output_path = output_dir / filename

        data = {
            "source_id": source_id,
            "analyzed_at": datetime.now().isoformat(),
            "model_used": self.client.model_name,
            "total_analyses": len(analyses),
            "analyses": [a.model_dump(mode="json") for a in analyses],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return output_path


def analyze_source_tweets(
    source_id: str,
    data_dir: Path | None = None,
    api_key: str | None = None,
    model: str = "claude-sonnet-4-20250514",
    max_tweets: int | None = None,
    progress_callback: callable | None = None,
) -> list[TweetAnalysis]:
    """Convenience function to analyze all tweets from a source.

    Args:
        source_id: Twitter source to analyze.
        data_dir: Base data directory.
        api_key: Anthropic API key.
        model: Model to use.
        max_tweets: Maximum tweets to analyze.
        progress_callback: Optional progress callback.

    Returns:
        List of TweetAnalysis objects.
    """
    data_dir = Path(data_dir or "data")
    storage = TweetStorage(data_dir)
    analyzer = TweetAnalyzer(api_key=api_key, model=model)

    # Load tweets with tickers
    tweets = list(storage.load_tweets(source_id))

    # Filter to tweets with tickers
    tweets_with_tickers = []
    for tweet in tweets:
        tweet.extract_entities()
        if tweet.mentioned_tickers:
            tweets_with_tickers.append(tweet)

    if max_tweets:
        tweets_with_tickers = tweets_with_tickers[:max_tweets]

    return analyzer.analyze_tweets(
        tweets_with_tickers,
        filter_with_tickers=False,  # Already filtered
        progress_callback=progress_callback,
    )
