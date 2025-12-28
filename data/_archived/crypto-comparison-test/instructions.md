# Crypto Sentiment Analysis - Comparison Test

This is a comparison test between Claude Code and Opencode/GLM-4.7.
Both AI tools should analyze the same transcript and produce structured JSON output.

---

## Episode Information

| Field | Value |
|-------|-------|
| Video ID | `F6Azi0j8A70` |
| Source Type | youtube |
| Channel | TechnicalRoundup |
| Date | **2025-07-18** |
| Transcript | `transcript.txt` (same folder) |

---

## Hosts

| Host | Aliases |
|------|---------|
| **Cred** | CryptoCred, CC |
| **Duck** | Don, DonAlt, CryptoDonAlt |

**Note:** Cred and Duck are two different people. Duck is the same person as "Don" and "DonAlt".

**Speaker Identification Tips:**
- Look for names mentioned in dialogue (e.g., "What do you think, Don?")
- `>>` in transcripts indicates speaker change
- If unsure, set speaker to "Unknown"

---

## Your Task

1. Read the transcript file: `transcript.txt`
2. Analyze for crypto asset mentions
3. Extract structured sentiment data
4. Save output to the correct folder (see below)

---

## Output Path

**If you are Claude Code:**
Save to: `claude-code/F6Azi0j8A70.json`

**If you are Opencode/GLM-4.7:**
Save to: `opencode-glm/F6Azi0j8A70.json`

---

## Analysis Guidelines

### Sentiment Classification (Be CONSERVATIVE)

| Language | Classification |
|----------|----------------|
| "Could go up", "might be interesting" | `neutral` |
| "I'm buying more", "accumulating", "DCA" | `bullish` |
| "Time to take profits", "I'm selling" | `bearish` |
| "Definitely going to moon" | `very_bullish` |
| "This is going to zero" | `very_bearish` |

### Crypto Terminology

**Bullish signals:** moon, accumulating, DCA, buying the dip, undervalued, oversold, bottom is in, higher lows

**Bearish signals:** dead cat bounce, exit liquidity, top signal, overextended, overbought, lower highs, distribution

**Neutral signals:** consolidation, ranging, wait and see, choppy, sideways

### Recommendation Type (CRITICAL)

| Type | Examples |
|------|----------|
| `active_position` | "I own BTC", "I'm long ETH" |
| `entry_signal` | "I'm buying here", "Good entry" |
| `exit_signal` | "Taking profits", "I sold" |
| `price_call` | "BTC to 150k" (prediction, no entry) |
| `commentary` | "BTC looks interesting" (no action) |

### Invalidation Price

If speaker mentions a price that invalidates their thesis:
- "Bullish unless 108k breaks" → `invalidation_price: 108000`
- If not mentioned → `invalidation_price: null`

### Is New Position

- `true`: NEW call/trade/position
- `false`: Repeating previous stance ("As I said last week...")

---

## JSON Schema

Output ONLY valid JSON matching this schema:

```json
{
  "source_id": "F6Azi0j8A70",
  "source_type": "youtube",
  "channel_or_podcast": "TechnicalRoundup",
  "date": "2025-07-18",
  "speakers": ["Cred", "Duck"],
  "main_topics": ["Max 5 main topics"],
  "assets_discussed": ["BTC", "ETH", "etc"],
  "mentions": [
    {
      "asset_name": "Bitcoin",
      "asset_symbol": "BTC",
      "asset_type": "coin|token|stablecoin|nft|defi",
      "sentiment": "very_bullish|bullish|neutral|bearish|very_bearish",
      "confidence": "high|medium|low|speculative",
      "speaker": "Cred|Duck|Unknown",
      "timestamp": null,
      "quote": "Exact quote from transcript (max 500 chars)",
      "reasoning": "Why this sentiment was assigned",
      "price_prediction": "Verbal prediction if made",
      "price_target": 150000,
      "price_target_currency": "USD",
      "time_horizon": "end of 2025",
      "market_cap_awareness": false,
      "mentioned_catalysts": ["ETF", "halving"],
      "risk_factors_mentioned": ["regulation"],
      "recommendation_type": "active_position|entry_signal|exit_signal|price_call|commentary",
      "invalidation_price": null,
      "is_new_position": true
    }
  ],
  "overall_market_sentiment": "very_bullish|bullish|neutral|bearish|very_bearish",
  "bitcoin_dominance_view": "increasing|decreasing|stable|not_discussed",
  "alt_season_prediction": true,
  "summary": "3-5 sentence summary of crypto discussion",
  "key_takeaways": [
    "Takeaway 1",
    "Takeaway 2",
    "Takeaway 3"
  ],
  "transcript_word_count": 42000,
  "has_timestamps": true,
  "model_used": "YOUR_MODEL_NAME"
}
```

---

## Field Definitions

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `source_id` | string | yes | Video ID |
| `date` | string | yes | YYYY-MM-DD format |
| `speakers` | array | yes | List identified speakers |
| `mentions` | array | yes | One entry per crypto mention |
| `sentiment` | enum | yes | very_bullish/bullish/neutral/bearish/very_bearish |
| `confidence` | enum | yes | high/medium/low/speculative |
| `recommendation_type` | enum | yes | active_position/entry_signal/exit_signal/price_call/commentary |
| `invalidation_price` | number/null | yes | Price level or null |
| `is_new_position` | boolean | yes | true/false |
| `model_used` | string | yes | Your model name (e.g., "claude-opus-4-5" or "glm-4.7") |

---

## Important Notes

1. **Only include assets with CLEAR sentiment** - don't force mentions
2. **Be conservative** - use "neutral" when uncertain
3. **Exact quotes** - copy actual words from transcript
4. **Attribute speakers** - Cred or Duck when identifiable
5. **Valid JSON** - ensure output is parseable

---

## Begin Analysis

Read `transcript.txt` and produce your JSON output.
