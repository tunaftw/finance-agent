# TechnicalRoundup Crypto Analysis Workflow

Master instruction document for downloading, transcribing, and analyzing TechnicalRoundup YouTube videos.

---

## Overview

This document describes the complete pipeline to:
1. **Collect** YouTube transcripts from TechnicalRoundup
2. **Prepare** transcripts for crypto sentiment analysis
3. **Analyze** each transcript and extract structured data
4. **Save** results as JSON with completion tracking

**Target output:** JSON files with crypto asset mentions, sentiment, price predictions, and accuracy-tracking metadata.

---

## Prerequisites

### Required Tools
```bash
# Verify yt-dlp is installed
yt-dlp --version

# Verify podstock is available
python -m podstock --help
```

### Directory Structure
```
data/
├── youtube/
│   ├── channels.json           # Channel configurations
│   ├── videos.jsonl            # Video metadata
│   └── transcripts/
│       └── technicalroundup/   # Transcript .txt files
└── crypto/
    └── glm-batch/
        ├── completion-log.json # Progress tracking
        └── *.json              # Analysis output files
```

---

## Channel Information

### TechnicalRoundup
| Field | Value |
|-------|-------|
| Channel | TechnicalRoundup |
| URL | https://www.youtube.com/@TechnicalRoundup |
| Category | Crypto |
| Language | English |

### Hosts

| Host | Aliases | Notes |
|------|---------|-------|
| **Cred** | CryptoCred, CC | Usually the main host |
| **Duck** | Don, DonAlt, CryptoDonAlt | Same person as "Don" |

**Speaker Identification Tips:**
- Listen for names in dialogue (e.g., "What do you think, Don?")
- `>>` in transcripts indicates speaker change
- If unsure, set speaker to "Unknown"

---

## Step 1: Collect New Videos

Download transcripts from TechnicalRoundup's YouTube channel:

```bash
# Collect all videos (first run)
podstock youtube collect --channel technicalroundup

# Collect with limit (for testing)
podstock youtube collect --channel technicalroundup --max 10

# Check collection stats
podstock youtube stats
```

**What this does:**
- Fetches video metadata from YouTube
- Downloads auto-generated captions (or manual subtitles if available)
- Saves transcripts to `data/youtube/transcripts/technicalroundup/`
- Updates `data/youtube/videos.jsonl` with video metadata

---

## Step 2: Prepare Analysis Batch

Generate the batch instructions file:

```bash
podstock crypto prepare-batch --channel technicalroundup
```

**Output files created:**
- `data/crypto/glm-batch/transcript-queue.txt` - List of transcripts to process
- `data/crypto/glm-batch/completion-log.json` - Progress tracking
- `docs/CRYPTO-ANALYSIS-INSTRUCTIONS.md` - Batch-specific instructions (regenerated)

---

## Step 3: Analyze Transcripts

For each transcript, perform sentiment analysis and save structured JSON.

### 3.1 Read the Transcript

Read the full transcript file from `data/youtube/transcripts/technicalroundup/{video_id}.txt`

### 3.2 Get the Publish Date

**CRITICAL:** Always verify the date from the date table in `docs/CRYPTO-ANALYSIS-INSTRUCTIONS.md`.
Never guess dates - incorrect dates invalidate accuracy tracking.

### 3.3 Apply Analysis Guidelines

#### Sentiment Classification (Be CONSERVATIVE)

| Signal | Classification |
|--------|----------------|
| "Could go up", "might be interesting" | `neutral` |
| "I'm buying more", "accumulating", "DCA" | `bullish` |
| "Time to take profits", "I'm selling" | `bearish` |
| "Definitely going to moon" | `very_bullish` |
| "This is going to zero" | `very_bearish` |

#### Crypto-Specific Terminology

**Bullish:** moon, accumulating, DCA, buying the dip, undervalued, oversold, bottom is in, higher lows

**Bearish:** dead cat bounce, exit liquidity, top signal, overextended, overbought, lower highs, distribution

**Neutral:** consolidation, ranging, wait and see, choppy, sideways

#### Recommendation Type (CRITICAL for accuracy tracking)

| Type | Examples | Description |
|------|----------|-------------|
| `active_position` | "I own BTC", "I'm long ETH" | Speaker states current position |
| `entry_signal` | "I'm buying here", "Good entry" | Recommends buying now |
| `exit_signal` | "Taking profits", "I sold" | Recommends selling |
| `price_call` | "BTC to 150k" | Price prediction without entry |
| `commentary` | "BTC looks interesting" | General sentiment, no action |

#### Invalidation Price

If the speaker mentions a price that would invalidate their thesis, capture it:
- "Bullish unless 108k breaks" → `invalidation_price: 108000`
- "If we lose 2.5k on ETH, I'm out" → `invalidation_price: 2500`
- If not mentioned → `invalidation_price: null`

#### Is New Position

- `true`: This is a NEW call/trade/position
- `false`: Repeating previous stance ("As I said last week...")

### 3.4 Generate JSON Output

Save to `data/crypto/glm-batch/{video_id}.json`

---

## JSON Schema

```json
{
  "source_id": "VIDEO_ID",
  "source_type": "youtube",
  "channel_or_podcast": "TechnicalRoundup",
  "date": "YYYY-MM-DD",
  "speakers": ["Cred", "Duck"],
  "main_topics": ["Topic 1", "Topic 2"],
  "assets_discussed": ["BTC", "ETH"],
  "mentions": [
    {
      "asset_name": "Bitcoin",
      "asset_symbol": "BTC",
      "asset_type": "coin",
      "sentiment": "very_bullish|bullish|neutral|bearish|very_bearish",
      "confidence": "high|medium|low|speculative",
      "speaker": "Cred",
      "timestamp": null,
      "quote": "Exact quote from transcript (max 500 chars)",
      "reasoning": "Why this sentiment was assigned",
      "price_prediction": "Going to 150k",
      "price_target": 150000,
      "price_target_currency": "USD",
      "time_horizon": "end of 2025",
      "market_cap_awareness": false,
      "mentioned_catalysts": ["ETF inflows", "halving"],
      "risk_factors_mentioned": ["regulation"],
      "recommendation_type": "active_position|entry_signal|exit_signal|price_call|commentary",
      "invalidation_price": 108000,
      "is_new_position": true
    }
  ],
  "overall_market_sentiment": "bullish|neutral|bearish",
  "bitcoin_dominance_view": "increasing|decreasing|stable|not_discussed",
  "alt_season_prediction": true,
  "summary": "3-5 sentence summary of crypto discussion",
  "key_takeaways": [
    "Takeaway 1",
    "Takeaway 2",
    "Takeaway 3"
  ],
  "transcript_word_count": 10000,
  "has_timestamps": true,
  "model_used": "claude-opus-4-5-20251101"
}
```

### Schema Rules

| Field | Values |
|-------|--------|
| `sentiment` | very_bullish, bullish, neutral, bearish, very_bearish |
| `confidence` | high, medium, low, speculative |
| `asset_type` | coin, token, stablecoin, nft, defi |
| `recommendation_type` | active_position, entry_signal, exit_signal, price_call, commentary |
| `bitcoin_dominance_view` | increasing, decreasing, stable, not_discussed |

---

## Step 4: Save & Verify

### 4.1 Save JSON File

Save output to: `data/crypto/glm-batch/{source_id}.json`

Where `source_id` = video ID from filename (e.g., `K4XV1bEovtY` from `K4XV1bEovtY.txt`)

### 4.2 Update Completion Log

After each transcript, update `data/crypto/glm-batch/completion-log.json`:

```json
{
  "completed": [
    "VIDEO_ID_1.txt",
    "VIDEO_ID_2.txt"
  ],
  "failed": [],
  "total_processed": 2,
  "last_updated": "2025-12-26T14:30:00",
  "notes": "Crypto sentiment batch for TechnicalRoundup"
}
```

### 4.3 Verification Checklist

For each transcript:
- [ ] Read the full transcript
- [ ] Looked up correct date from date table
- [ ] Identified speakers (Cred vs Duck)
- [ ] Extracted all crypto asset mentions
- [ ] Assigned conservative sentiment
- [ ] Classified recommendation_type for each mention
- [ ] Captured invalidation_price if mentioned
- [ ] Generated valid JSON
- [ ] Saved to glm-batch/
- [ ] Updated completion-log.json

---

## Incremental Updates

When new TechnicalRoundup episodes are released:

```bash
# 1. Collect only new videos
podstock youtube collect --channel technicalroundup

# 2. Regenerate batch instructions (updates date table)
podstock crypto prepare-batch --channel technicalroundup

# 3. Check completion-log to see what's already done
cat data/crypto/glm-batch/completion-log.json

# 4. Analyze only transcripts NOT in "completed" array
```

The completion-log tracks which transcripts have been processed, so you only need to analyze new ones.

---

## Common Mistakes to Avoid

1. **Sponsors as mentions** - Don't extract sponsor messages as crypto mentions
2. **Uncertain sentiment** - Be conservative, use "neutral" when in doubt
3. **JSON syntax errors** - Validate JSON before saving
4. **Forgetting completion-log** - ALWAYS update after each transcript
5. **Wrong dates** - ALWAYS use date table, never guess
6. **Missing speaker** - Attribute quotes to Cred or Duck when identifiable

---

## Quick Reference

### CLI Commands
```bash
podstock youtube collect --channel technicalroundup     # Get transcripts
podstock youtube stats                                  # Check progress
podstock crypto prepare-batch --channel technicalroundup # Prepare batch
podstock crypto stats                                   # Analysis stats
```

### File Locations
| Purpose | Path |
|---------|------|
| Transcripts | `data/youtube/transcripts/technicalroundup/*.txt` |
| Analysis output | `data/crypto/glm-batch/*.json` |
| Completion log | `data/crypto/glm-batch/completion-log.json` |
| Batch instructions | `docs/CRYPTO-ANALYSIS-INSTRUCTIONS.md` |

---

## Example Analysis Output

```json
{
  "source_id": "F6Azi0j8A70",
  "source_type": "youtube",
  "channel_or_podcast": "TechnicalRoundup",
  "date": "2025-07-18",
  "speakers": ["Cred", "Duck"],
  "main_topics": ["ETH and XRP outperformance", "BTC pullback risk", "Mini alt season"],
  "assets_discussed": ["BTC", "ETH", "XRP"],
  "mentions": [
    {
      "asset_name": "Ethereum",
      "asset_symbol": "ETH",
      "asset_type": "coin",
      "sentiment": "bullish",
      "confidence": "high",
      "speaker": "Duck",
      "timestamp": null,
      "quote": "Looking at ETH and XRP especially, they look quite incredible. EBTC has been outperforming for basically weeks now. The main argument on ETHUSD was that if it breaks 2.8, there's mostly air towards four.",
      "reasoning": "Duck taking victory lap on ETH call, mentioned target of 4k from 2.8k breakout",
      "price_prediction": "Mostly air towards 4k",
      "price_target": 4000,
      "price_target_currency": "USD",
      "time_horizon": null,
      "market_cap_awareness": false,
      "mentioned_catalysts": ["breakout above 2.8k"],
      "risk_factors_mentioned": [],
      "recommendation_type": "price_call",
      "invalidation_price": null,
      "is_new_position": true
    }
  ],
  "overall_market_sentiment": "bullish",
  "bitcoin_dominance_view": "decreasing",
  "alt_season_prediction": true,
  "summary": "Casual Friday episode with both Cred and Duck discussing a 'mini alt season' as ETH and XRP outperform BTC.",
  "key_takeaways": [
    "Duck's ETH and XRP calls played out perfectly",
    "ETH target: 4k from 2.8k breakout",
    "BTC support at 115-116k for shallow pullback"
  ],
  "transcript_word_count": 42110,
  "has_timestamps": true,
  "model_used": "claude-opus-4-5-20251101"
}
```
