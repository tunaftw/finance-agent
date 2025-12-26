"""Crypto sentiment analysis module.

This module provides functionality for:
- Extracting crypto mentions and sentiment from transcripts
- Tracking bullish/bearish predictions over time
- Verifying predictions against actual price movements
- Generating bias tracking reports

Usage:
    from podstock.crypto import CryptoAnalyzer, CryptoMention

    analyzer = CryptoAnalyzer(llm_client)
    analysis = analyzer.analyze_transcript(transcript_path)
"""

from podstock.crypto.models import (
    AggregatedSentiment,
    CryptoAsset,
    CryptoMention,
    CryptoSentimentAnalysis,
    PricePrediction,
    SentimentLevel,
)

__all__ = [
    "CryptoAsset",
    "SentimentLevel",
    "CryptoMention",
    "CryptoSentimentAnalysis",
    "PricePrediction",
    "AggregatedSentiment",
]
