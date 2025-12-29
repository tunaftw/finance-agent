# Twitter API Collection Method

Automated tweet collection using twitterapi.io service.

## Prerequisites

API-nyckeln finns i `.env` i repo-roten. **Alla Python-anrop ska börja med:**

```python
from dotenv import load_dotenv
load_dotenv()
```

## Step-by-Step Process

### 1. Verify API Key

```python
from dotenv import load_dotenv
import os
load_dotenv()
key = os.getenv('TWITTER_API_KEY', '')
print(f"API key loaded: {key[:10]}..." if key else "No API key found in .env")
```

### 2. Check Current State

```bash
python -c "
import json
from pathlib import Path

handle = 'HANDLE_HERE'  # Replace with actual handle (without @)
state_file = Path('data/twitter/state.json')

if state_file.exists():
    state = json.loads(state_file.read_text())
    if handle in state:
        info = state[handle]
        print(f'Last collection: {info.get(\"last_collected_at\", \"Never\")}')
        print(f'Tweets stored: {info.get(\"tweet_count\", 0)}')
        print(f'Newest tweet ID: {info.get(\"last_tweet_id\", \"None\")}')
    else:
        print(f'No previous data for @{handle}')
else:
    print('No state file - first collection')
"
```

### 3. Run Collection

#### Option A: New Tweets Only (Incremental)

```python
from dotenv import load_dotenv
load_dotenv()

from podstock.twitter import collect_tweets

result = collect_tweets(
    source_id="HANDLE_HERE",  # without @
    max_tweets=1000,
    include_replies=True
)

print(f"Collected: {result.tweets_collected} tweets")
print(f"Total stored: {result.total_tweets}")
if result.error:
    print(f"Error: {result.error}")
```

#### Option B: Date-Filtered Collection

```python
from dotenv import load_dotenv
load_dotenv()

from podstock.twitter import collect_tweets
from datetime import date

result = collect_tweets(
    source_id="HANDLE_HERE",
    since=date(2024, 1, 1),    # Start date
    until=date(2024, 12, 31),  # End date
    max_tweets=10000,
    include_replies=True
)

print(f"Collected: {result.tweets_collected} tweets")
print(f"Total stored: {result.total_tweets}")
```

#### Option C: One-liner for Quick Collection

```bash
python -c "
from dotenv import load_dotenv
load_dotenv()

from podstock.twitter import collect_tweets
from datetime import date

result = collect_tweets(
    source_id='HANDLE_HERE',
    since=date(YEAR, MONTH, DAY),
    until=date(YEAR, MONTH, DAY),
    max_tweets=10000
)
print(f'Collected {result.tweets_collected} new tweets')
print(f'Total: {result.total_tweets} tweets stored')
print(f'Saved to: data/twitter/raw/HANDLE_HERE/tweets.jsonl')
cost = result.tweets_collected * 0.00015
print(f'Estimated cost: \${cost:.4f}')
"
```

### 4. Verify Storage

```bash
# Count tweets in storage
wc -l data/twitter/raw/HANDLE_HERE/tweets.jsonl

# View latest tweets
tail -3 data/twitter/raw/HANDLE_HERE/tweets.jsonl | python -m json.tool
```

## API Endpoints Used

| Endpoint | Use Case |
|----------|----------|
| `/twitter/user/last_tweets` | Recent tweets (no date filter) |
| `/twitter/tweet/advanced_search` | Date-filtered collection |

## Rate Limiting

- 5-second delay between API pages (built into client)
- Max 20 tweets per page
- If 429 error: wait 5 minutes, then retry

## Cost Calculation

```python
tweets_collected = 500  # Example
cost_per_1000 = 0.15
cost = (tweets_collected / 1000) * cost_per_1000
print(f"Cost: ${cost:.4f}")  # $0.0750
```

## Error Handling

```python
from podstock.twitter import collect_tweets
from podstock.twitter.exceptions import TwitterRateLimitError, TwitterCollectionError

try:
    result = collect_tweets(source_id="handle", max_tweets=500)
except TwitterRateLimitError:
    print("Rate limited - wait 5 minutes and retry")
except TwitterCollectionError as e:
    print(f"Collection failed: {e}")
```

## Full Example Session

```python
from dotenv import load_dotenv
load_dotenv()

from podstock.twitter import collect_tweets
from datetime import date

handle = "vildkatten"
since = date(2024, 1, 1)
until = date(2024, 12, 31)

print(f"Collecting tweets from @{handle}")
print(f"Period: {since} to {until}")

result = collect_tweets(
    source_id=handle,
    since=since,
    until=until,
    max_tweets=10000,
    include_replies=True
)

if result.success:
    cost = result.tweets_collected * 0.00015
    print(f"\n--- Summary ---")
    print(f"Tweets collected: {result.tweets_collected}")
    print(f"Total stored: {result.total_tweets}")
    print(f"Storage: data/twitter/raw/{handle}/tweets.jsonl")
    print(f"Estimated cost: ${cost:.4f}")
else:
    print(f"Error: {result.error}")
```
