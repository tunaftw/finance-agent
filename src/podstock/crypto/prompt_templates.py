"""Prompt templates for crypto sentiment extraction.

This module contains LLM prompts specifically designed for extracting
crypto sentiment, predictions, and market opinions from transcripts.
"""

CRYPTO_EXTRACTION_SYSTEM_PROMPT = """You are an expert at analyzing cryptocurrency content and extracting sentiment.

Your task is to carefully analyze transcripts from crypto podcasts/videos and identify:
1. SPECIFIC crypto asset mentions (BTC, ETH, SOL, etc.)
2. The sentiment expressed (very_bullish/bullish/neutral/bearish/very_bearish)
3. Any price predictions or targets
4. The reasoning behind their views
5. Risk factors or catalysts mentioned

## IMPORTANT GUIDELINES:

### Be CONSERVATIVE with sentiment classification:
- "Could go up" or "might be interesting" = neutral (NOT bullish)
- "I'm buying more" or "accumulating" = bullish
- "DCA every week" or "adding to position" = bullish
- "Time to take profits" or "I'm selling some" = bearish
- "Don't touch this" or "stay away" = bearish
- Strong conviction language like "definitely going to moon" = very_bullish
- Panic language like "this is going to zero" = very_bearish

### Capture EXACT quotes:
- Include the actual words spoken that support your sentiment classification
- Quotes should be 1-3 sentences, max 150 words
- Include any price targets or timeline mentioned

### Note speaker knowledge:
- Set market_cap_awareness=true if they mention market cap, fully diluted valuation, tokenomics
- List specific catalysts (ETF approval, halving, upgrade, regulation, etc.)
- List risk factors they mention (regulation, competition, technical issues, etc.)

### Speaker Identification (CRITICAL):
- Each mention MUST have the correct speaker if identifiable
- Look for names mentioned in dialogue (e.g., "What do you think, Don?")
- The ">>" marker in transcripts indicates a speaker change
- Use the host information provided in the instructions (if available)
- If unsure, set speaker to "Unknown" rather than guessing
- The speakers array at the top level should list all identified speakers
- This is important for tracking individual analyst accuracy over time

### Recommendation Classification (CRITICAL for accuracy tracking):

For each mention, you MUST classify:

1. **recommendation_type** (required):
   - "active_position": Speaker states they own/are long/short ("I own BTC", "I'm long ETH", "I have a position")
   - "entry_signal": Speaker recommends buying here ("I'm buying", "Good entry", "Adding here", "This is a buy")
   - "exit_signal": Speaker recommends selling ("Taking profits", "I sold", "Reducing position", "Time to exit")
   - "price_call": Price prediction without entry recommendation ("BTC to 150k", "I think ETH hits 4k")
   - "commentary": General sentiment, no actionable advice ("BTC looks interesting", "Could be good", "Watching this")

2. **invalidation_price** (if mentioned):
   - The price level that would invalidate their thesis
   - "Bullish unless 108k breaks" → invalidation_price: 108000
   - "If we lose 2.5k on ETH, I'm out" → invalidation_price: 2500
   - If not mentioned, set to null

3. **is_new_position** (required):
   - true: This is a NEW call/trade/position being announced
   - false: Repeating or confirming previous stance ("As I said last week...", "Still bullish as before")

### CRYPTO-SPECIFIC TERMINOLOGY:
Bullish signals: "moon", "accumulating", "DCA", "buying the dip", "undervalued", "oversold", "bottom is in", "higher lows"
Bearish signals: "dead cat bounce", "exit liquidity", "top signal", "overextended", "overbought", "lower highs", "distribution"
Neutral signals: "consolidation", "ranging", "wait and see", "choppy", "sideways"

## OUTPUT FORMAT:
Return ONLY valid JSON matching the schema. No markdown, no explanation."""

CRYPTO_EXTRACTION_USER_PROMPT = """Analyze the following cryptocurrency transcript and extract sentiment information.

## SOURCE INFORMATION:
- Source ID: {source_id}
- Source Type: {source_type}
- Channel/Podcast: {channel_name}
- Date: {date}
- Title: {title}

## TRANSCRIPT:
---
{transcript}
---

## REQUIRED OUTPUT:
Extract the following as JSON:

```json
{{
  "speakers": ["List of speaker names if identifiable"],
  "main_topics": ["Max 5 main topics discussed"],
  "assets_discussed": ["BTC", "ETH", "All crypto symbols mentioned"],
  "mentions": [
    {{
      "asset_name": "Bitcoin",
      "asset_symbol": "BTC",
      "asset_type": "coin",
      "sentiment": "bullish|bearish|neutral|very_bullish|very_bearish",
      "confidence": "high|medium|low|speculative",
      "speaker": "Name if known",
      "timestamp": "MM:SS if available",
      "quote": "Exact quote supporting this sentiment",
      "reasoning": "Why this sentiment was assigned",
      "price_prediction": "Verbal prediction if made",
      "price_target": 150000,
      "price_target_currency": "USD",
      "time_horizon": "end of 2025",
      "market_cap_awareness": true,
      "mentioned_catalysts": ["ETF", "halving"],
      "risk_factors_mentioned": ["regulation"],
      "recommendation_type": "active_position|entry_signal|exit_signal|price_call|commentary",
      "invalidation_price": 108000,
      "is_new_position": true
    }}
  ],
  "overall_market_sentiment": "bullish|bearish|neutral|very_bullish|very_bearish",
  "bitcoin_dominance_view": "increasing|decreasing|stable|not_discussed",
  "alt_season_prediction": true|false|null,
  "summary": "3-5 sentences summarizing the crypto content",
  "key_takeaways": ["3-5 bullet points"]
}}
```

Remember:
- Only include assets with CLEAR sentiment expressions
- Be conservative - neutral unless clearly bullish/bearish
- Include exact quotes
- Note any specific price targets or timelines"""

CRYPTO_FEW_SHOT_EXAMPLE = """
## EXAMPLE INPUT:
Transcript from "Technical Roundup" dated 2025-01-15:

"[12:45] Look, Bitcoin at 95K, I think we're going to 150K by end of 2025. The ETF flows are insane, institutional adoption is here. I'm still accumulating, dollar cost averaging every week. [15:20] Now Ethereum is a different story. The Pectra upgrade is coming but I'm not as bullish. I'd say neutral to slightly bullish on ETH, maybe hold your current position. [18:30] Stay away from Solana here, it's way overextended after that pump. Classic dead cat bounce territory."

## EXAMPLE OUTPUT:
```json
{
  "speakers": ["Unknown Host"],
  "main_topics": ["Bitcoin price prediction", "Ethereum outlook", "Solana warning"],
  "assets_discussed": ["BTC", "ETH", "SOL"],
  "mentions": [
    {
      "asset_name": "Bitcoin",
      "asset_symbol": "BTC",
      "asset_type": "coin",
      "sentiment": "very_bullish",
      "confidence": "high",
      "speaker": null,
      "timestamp": "12:45",
      "quote": "Bitcoin at 95K, I think we're going to 150K by end of 2025. The ETF flows are insane, institutional adoption is here. I'm still accumulating, dollar cost averaging every week.",
      "reasoning": "Speaker gives specific price target (58% upside), is actively accumulating via DCA, cites ETF flows and institutional adoption as catalysts",
      "price_prediction": "150K by end of 2025",
      "price_target": 150000,
      "price_target_currency": "USD",
      "time_horizon": "end of 2025",
      "market_cap_awareness": false,
      "mentioned_catalysts": ["ETF flows", "institutional adoption"],
      "risk_factors_mentioned": [],
      "recommendation_type": "active_position",
      "invalidation_price": null,
      "is_new_position": true
    },
    {
      "asset_name": "Ethereum",
      "asset_symbol": "ETH",
      "asset_type": "coin",
      "sentiment": "neutral",
      "confidence": "medium",
      "speaker": null,
      "timestamp": "15:20",
      "quote": "Now Ethereum is a different story. The Pectra upgrade is coming but I'm not as bullish. I'd say neutral to slightly bullish on ETH, maybe hold your current position.",
      "reasoning": "Speaker explicitly says 'neutral to slightly bullish' and recommends holding, not adding. Less conviction than BTC.",
      "price_prediction": null,
      "price_target": null,
      "price_target_currency": "USD",
      "time_horizon": null,
      "market_cap_awareness": false,
      "mentioned_catalysts": ["Pectra upgrade"],
      "risk_factors_mentioned": [],
      "recommendation_type": "commentary",
      "invalidation_price": null,
      "is_new_position": true
    },
    {
      "asset_name": "Solana",
      "asset_symbol": "SOL",
      "asset_type": "coin",
      "sentiment": "bearish",
      "confidence": "high",
      "speaker": null,
      "timestamp": "18:30",
      "quote": "Stay away from Solana here, it's way overextended after that pump. Classic dead cat bounce territory.",
      "reasoning": "Speaker explicitly says 'stay away', uses bearish terminology 'overextended' and 'dead cat bounce'",
      "price_prediction": null,
      "price_target": null,
      "price_target_currency": "USD",
      "time_horizon": null,
      "market_cap_awareness": false,
      "mentioned_catalysts": [],
      "risk_factors_mentioned": ["overextended", "dead cat bounce"],
      "recommendation_type": "exit_signal",
      "invalidation_price": null,
      "is_new_position": true
    }
  ],
  "overall_market_sentiment": "bullish",
  "bitcoin_dominance_view": "not_discussed",
  "alt_season_prediction": null,
  "summary": "The host is very bullish on Bitcoin with a 150K target by end of 2025, citing ETF flows and institutional adoption. They are DCA-ing weekly. On Ethereum, sentiment is neutral despite the upcoming Pectra upgrade. The host warns to stay away from Solana, calling it overextended and a dead cat bounce.",
  "key_takeaways": [
    "BTC target: $150K by end of 2025 (currently $95K)",
    "Host is actively accumulating BTC via weekly DCA",
    "ETH: Hold but don't add, neutral outlook despite Pectra upgrade",
    "SOL: Avoid, overextended after recent pump",
    "Overall crypto market sentiment is bullish, driven by institutional flows"
  ]
}
```
"""

# Shorter version for batch processing
CRYPTO_EXTRACTION_SHORT_PROMPT = """Extract crypto sentiment from this transcript. Return JSON only.

Source: {source_id} ({source_type})
Channel: {channel_name}
Date: {date}

TRANSCRIPT:
{transcript}

Return JSON with: speakers, assets_discussed, mentions (with sentiment, quote, reasoning), overall_market_sentiment, summary."""
