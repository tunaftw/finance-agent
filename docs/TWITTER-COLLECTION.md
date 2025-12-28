# Twitter Tweet Collection Guide

This guide covers the optimized workflow for collecting tweets from Twitter/X accounts.

## Overview

PodStock uses browser automation to collect tweets from financial analysts, podcast hosts, and other stock market commentators. The system includes:

- **Coverage Analysis**: Track which periods have been collected
- **Gap Detection**: Identify missing or incomplete periods
- **Deduplication**: Avoid downloading duplicate tweets
- **Rate Limit Awareness**: Work within Twitter's limits

## Rate Limits

| Account Type | Daily Limit | 15-min Window |
|--------------|-------------|---------------|
| Free | ~1,000 posts | ~100-200 posts |
| Premium | ~10,000 posts | ~500+ posts |

**Triggers for rate limits:**
- Scrolling too fast (>50 tweets/min)
- Many requests in short time
- Non-human-like behavior

## CLI Commands

### Coverage Analysis

Show collection status for a source:

```bash
podstock twitter coverage vildkatten
```

Output:
```
Coverage Analysis: @vildkatten
============================================================

Total tweets: 580
Date range: 2024-03-28 -> 2025-12-25

Complete months (5):
  2025-01: 124 tweets
  2025-02: 175 tweets
  ...

Incomplete months (10):
  2024-03: 5 tweets (< 20)
  ...

Missing months (7):
  2024-04
  2024-05
  ...

Recommendations:
  - Collect missing periods: 2024-04, 2024-05, ...
  - Re-scan incomplete periods: 2024-03, 2024-06, ...
```

### Generate Search URLs

Generate a Twitter advanced search URL:

```bash
podstock twitter url vildkatten --since 2024-04-01 --until 2024-05-01
```

### Other Commands

```bash
# List Twitter sources
podstock twitter list

# Add a new source
podstock twitter add @username --category analyst

# Show statistics
podstock twitter stats

# Rebuild search index
podstock twitter rebuild-index
```

## Python Script

The `scripts/twitter_collect.py` script provides lower-level utilities:

```bash
# Coverage analysis
python scripts/twitter_collect.py coverage vildkatten

# Generate URLs for gaps
python scripts/twitter_collect.py urls vildkatten --mode gaps-only

# Export existing IDs (for browser dedup)
python scripts/twitter_collect.py ids vildkatten

# Save tweets from browser JSON
python scripts/twitter_collect.py save vildkatten --data '[{"id":"123",...}]'
```

## Collection Workflow

### 1. Analyze Current State

```bash
podstock twitter coverage vildkatten
```

### 2. Generate Search URL

```bash
podstock twitter url vildkatten --since 2024-04-01 --until 2024-05-01
```

### 3. Navigate and Collect

Open the URL in browser (must be logged into Twitter).

Initialize collection:
```javascript
window.collectedTweets = {};
```

Run batch collection (repeat until newThisBatch=0 twice):
```javascript
var articles = document.querySelectorAll('article[data-testid="tweet"]');
var newCount = 0; var lastDate = null;
articles.forEach(function(article) {
  try {
    var link = article.querySelector('a[href*="/status/"]');
    var id = link ? link.href.split('/status/')[1].split('?')[0] : null;
    var timeEl = article.querySelector('time');
    var posted = timeEl ? timeEl.getAttribute('datetime') : null;
    if (posted) lastDate = posted;
    if (id && !window.collectedTweets[id]) {
      var textEl = article.querySelector('div[data-testid="tweetText"]');
      var text = textEl ? textEl.textContent : '';
      if (text) {
        window.collectedTweets[id] = {id:id, text:text, posted:posted};
        newCount++;
      }
    }
  } catch(e) {}
});
window.scrollBy(0, 2000);
({total: Object.keys(window.collectedTweets).length, newThisBatch: newCount, lastDate: lastDate})
```

### 4. Save Tweets

Export from browser:
```javascript
JSON.stringify(Object.values(window.collectedTweets))
```

Save to storage:
```bash
python scripts/twitter_collect.py save vildkatten --data '{json}'
```

### 5. Verify

```bash
podstock twitter coverage vildkatten
```

## Deduplication

### Pre-collection Check

Load existing IDs before collection:
```bash
python scripts/twitter_collect.py ids vildkatten
```

In browser:
```javascript
window.existingIds = new Set([...]);  // Paste IDs
```

### Modified Collection Loop

Skip already-collected tweets:
```javascript
if (id && !window.existingIds.has(id) && !window.collectedTweets[id]) {
  // Collect only NEW tweets
}
```

### Post-save Deduplication

The save script automatically skips duplicates:
```
Saved: 47, Skipped: 12
Total tweets now: 627
```

## Session Planning

For free accounts, plan collection across multiple days:

| Day | Period | Expected |
|-----|--------|----------|
| 1 | Q4 2024 | ~300 tweets |
| 2 | Q3 2024 | ~300 tweets |
| 3 | Q2 2024 | ~300 tweets |
| 4 | Q1 2024 | ~300 tweets |

Within each session:
- Max 15-20 tweets per scroll
- 2-3 second delay between scrolls
- Pause 5 min if rate limited
- Max 200-300 tweets per 15-min window

## Data Storage

Tweets are stored in JSONL format:
```
data/twitter/raw/{source_id}/tweets.jsonl
```

Each tweet includes:
- `id`: Twitter's unique tweet ID
- `source_id`: Internal source identifier
- `author_handle`: Twitter handle
- `text`: Full tweet text
- `posted_at`: When posted (ISO timestamp)
- `collected_at`: When we collected it
- `mentioned_tickers`: Extracted $TICKER symbols
- `mentioned_users`: @mentioned users
- `hashtags`: #hashtags

## Troubleshooting

**"Something went wrong" error:**
Click Retry or reload the page. This happens when Twitter detects unusual activity.

**No tweets loading:**
Ensure you're logged into Twitter. Advanced search requires authentication.

**Rate limit hit:**
Wait 15 minutes before continuing.

**Curly quotes in JSON:**
The save script automatically converts fancy quotes to standard quotes.

## Files

| File | Purpose |
|------|---------|
| `scripts/twitter_collect.py` | Collection utilities |
| `src/podstock/twitter/storage.py` | JSONL storage |
| `src/podstock/twitter/state.py` | State tracking |
| `src/podstock/cli.py` | CLI commands |
| `.claude/commands/twitter-collect.md` | Claude skill |
