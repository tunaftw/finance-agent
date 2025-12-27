# Twitter Tweet Analysis Instructions

## Overview

This document describes how to analyze collected tweets for stock recommendations and investment insights.

**Key principle**: The analysis is performed by the AI agent itself (Claude Code or OpenCode) - NOT via external API calls. The agent reads the tweets and extracts insights directly.

## Analysis Environment Options

| Environment | How to Run |
|-------------|-----------|
| **Claude Code** | Run analysis directly in conversation. Agent reads tweets and outputs structured analysis. |
| **OpenCode** | Same approach - agent reads tweets and analyzes them in the session. |

Both environments work identically: the agent doing the analysis IS the LLM. No external API key needed.

## Why Agent-Based Analysis?

1. **No API key management** - The agent analyzing is the same agent running the session
2. **Context awareness** - Agent can reference previous messages, ask clarifying questions
3. **Flexible detection** - Not limited to `$TICKER` patterns, can detect company names, sentiment, etc.
4. **Language agnostic** - Works for Swedish, English, Norwegian tweets without modification

## Important: Ticker Detection Limitations

The current codebase has a `$TICKER` pattern filter that MISSES most tweets:

```python
# Current limitation (models.py line 149):
ticker_pattern = r"\$([A-Z]{1,5}(?:-[A-Z])?)"
```

This misses:
- "Köpte Saab idag" (Swedish style, no $)
- "Bullish on Evolution Gaming" (company name, no ticker)
- "Added more Bitcoin" (crypto without $BTC)
- "Rheinmetall ser intressant ut" (German company mentioned by name)

**The agent-based analysis solves this** by reading ALL tweets and using LLM intelligence to detect investment-relevant content.

## Running Analysis in Claude Code

### Step 1: Load tweets
```bash
# Count tweets per source
wc -l data/twitter/raw/*/tweets.jsonl

# Sample a source
head -20 data/twitter/raw/palma_fire/tweets.jsonl | python3 -c "import json,sys; [print(json.loads(l)['text'][:100]) for l in sys.stdin]"
```

### Step 2: Ask the agent to analyze
Example prompt:
> "Analysera de senaste 50 tweetsen från palma_fire. Identifiera alla aktierekommendationer, köp/sälj-signaler och marknadssentiment. Inkludera även omnämnanden av bolag utan $-symbol."

### Step 3: Agent outputs structured analysis
The agent will read the tweets and output:
- Stock mentions (with or without $ symbol)
- Buy/sell/hold signals
- Confidence level
- Relevant quotes

## Output Format

The agent should produce JSON-compatible output:

```json
{
  "source_id": "palma_fire",
  "analyzed_at": "2025-12-26T15:30:00",
  "total_tweets_reviewed": 50,
  "analyses": [
    {
      "tweet_id": "1234567890",
      "text_snippet": "Aktieportföljen upp 50% i år...",
      "stock_mentions": [
        {
          "stock_name": "Saab",
          "ticker": "SAAB-B",
          "action": "hold",
          "confidence": "high",
          "reasoning": "Explicit portfolio holding mentioned"
        }
      ],
      "market_sentiment": "bullish",
      "is_actionable": false
    }
  ]
}
```

## Batch Analysis Workflow

For large datasets, process in batches:

1. **Sample first** - Analyze 20-50 tweets to understand the account's style
2. **Filter by relevance** - Skip retweets, @replies to unrelated topics
3. **Focus on original content** - Prioritize original tweets over conversations
4. **Date range** - Analyze recent tweets first (last 3-6 months most relevant)

## Saving Results

After analysis, save to:
```
data/twitter/analyses/{source_id}-analysis.json
```

## CLI Reference (for programmatic use)

The CLI commands exist but require ANTHROPIC_API_KEY for external calls:
```bash
# These require API key (external LLM call):
podstock twitter analyze --source vildkatten --max 100
podstock twitter report --source vildkatten
```

**Prefer agent-based analysis** (this document) for:
- No API key setup
- Better detection (not limited to $TICKER)
- Interactive refinement

## Best Practices

1. **Read before analyzing** - Understand the account's posting style
2. **Batch appropriately** - 20-50 tweets per analysis pass
3. **Note confidence levels** - "Köpte Saab" = high confidence, "tittar på..." = low
4. **Preserve context** - Quote relevant portions of tweets
5. **Track dates** - Investment advice has a shelf life
