---
name: twitter-download
description: >-
  Download tweets from Twitter/X users. Use when user wants to collect,
  download, fetch, or sync tweets from a specific Twitter handle.
---

# Twitter Download Skill

Download tweets from Twitter/X accounts with automatic storage and deduplication.

## Quick Start

1. Ask user for **method**: Twitter API (recommended) or Browser scraping
2. Ask user for **handle**: Twitter username (e.g., @vildkatten)
3. Ask user for **time period**: All tweets, specific year/month, or new since last download
4. Execute collection and provide summary

## Method Selection

| Method | When to use |
|--------|-------------|
| **Twitter API** | Default. Fast, automated. Costs $0.15/1000 tweets. |
| **Browser scraping** | No API key, or API issues. Manual, slower, free. |

## Workflow

### Step 1: Gather Requirements

Ask the user (use AskUserQuestion tool):

```
1. Collection method?
   - Twitter API (Recommended) - automated, costs credits
   - Browser scraping - manual, free

2. Twitter handle? (e.g., @vildkatten)

3. Time period?
   - New tweets since last download (check state.json)
   - All tweets from [year] (e.g., 2024)
   - Specific month (e.g., January 2025)
   - All tweets ever
```

### Step 2: Check Existing State

Before collection, check what we already have:

```bash
# Read state for this user
python -c "
import json
from pathlib import Path
state_file = Path('data/twitter/state.json')
if state_file.exists():
    state = json.loads(state_file.read_text())
    handle = 'USERNAME_HERE'  # Replace with actual handle
    if handle in state:
        s = state[handle]
        print(f'Last collected: {s.get(\"last_collected_at\", \"Never\")}')
        print(f'Tweet count: {s.get(\"tweet_count\", 0)}')
        print(f'Last tweet ID: {s.get(\"last_tweet_id\", \"None\")}')
    else:
        print('No previous collection for this user')
else:
    print('No state file found')
"
```

### Step 3: Execute Collection

**For Twitter API method:** See [references/api-method.md](references/api-method.md)

**For Browser scraping method:** See [references/scraping-method.md](references/scraping-method.md)

### Step 4: Provide Summary

After collection, report:
- Number of tweets downloaded
- Storage location: `data/twitter/raw/{handle}/tweets.jsonl`
- Estimated cost (API only): tweets_collected * $0.00015
- Total tweets now stored for this user

## Storage Format

Tweets are stored in JSONL format at `data/twitter/raw/{handle}/tweets.jsonl`:

```json
{
  "id": "1234567890",
  "source_id": "vildkatten",
  "author_handle": "vildkatten",
  "text": "Tweet content here",
  "posted_at": "2024-12-28T10:30:00Z",
  "collected_at": "2024-12-28T15:00:00.123456",
  "likes": 42,
  "retweets": 5,
  "replies": 3,
  "views": 1500,
  "mentioned_tickers": ["$TSLA"],
  "mentioned_users": ["elonmusk"],
  "hashtags": ["stocks"]
}
```

## Date Range Shortcuts

| User says | Interpretation |
|-----------|----------------|
| "new tweets" / "update" | From last_collected_at to today |
| "2024" / "year 2024" | 2024-01-01 to 2024-12-31 |
| "jan 2025" / "january 2025" | 2025-01-01 to 2025-01-31 |
| "all tweets" / "everything" | No date filter (expensive!) |
| "last month" | Previous calendar month |
| "this year" | Current year start to today |

## Cost Estimation (API)

- $0.15 per 1,000 tweets
- Minimum charge: $0.00015 per API call

| Tweets | Cost |
|--------|------|
| 100 | ~$0.02 |
| 500 | ~$0.08 |
| 1,000 | $0.15 |
| 5,000 | $0.75 |
| 10,000 | $1.50 |

## API Key Configuration

API-nyckeln laddas automatiskt från `.env` i repo-roten:

```
# .env
TWITTER_API_KEY=your_key_here
```

Alla Python-anrop ska inkludera:
```python
from dotenv import load_dotenv
load_dotenv()  # Laddar TWITTER_API_KEY automatiskt
```

## Error Handling

| Error | Solution |
|-------|----------|
| `TWITTER_API_KEY not set` | Kontrollera att `.env` finns och innehåller nyckeln |
| `Rate limit exceeded` | Wait 5 minutes, then retry |
| `User not found` | Verify handle spelling |
| `No tweets in period` | Try different date range |
