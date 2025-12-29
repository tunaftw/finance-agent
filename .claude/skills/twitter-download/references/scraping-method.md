# Browser Scraping Collection Method

Manual tweet collection using browser automation. Free but requires user interaction.

## Prerequisites

- User must be logged into Twitter/X in their browser
- MCP browser tools available (claude-in-chrome)

## Step-by-Step Process

### 1. Analyze Current Coverage

```bash
python scripts/twitter_collect.py coverage HANDLE_HERE
```

Output shows:
- Complete months (20+ tweets)
- Incomplete months (<20 tweets)
- Missing months (0 tweets)

### 2. Get Existing Tweet IDs

To avoid duplicates, load existing IDs:

```bash
python scripts/twitter_collect.py ids HANDLE_HERE
```

Store in browser console:
```javascript
window.existingIds = new Set([/* paste IDs here */]);
```

### 3. Generate Search URL

```bash
python scripts/twitter_collect.py url HANDLE_HERE --since 2024-01-01 --until 2024-12-31
```

This outputs a URL like:
```
https://x.com/search?q=from:HANDLE_HERE since:2024-01-01 until:2024-12-31&f=live
```

### 4. Navigate to URL

Use browser automation to navigate:
```
Navigate to the generated Twitter search URL
```

Wait for page to load completely.

### 5. Initialize Collection

Run in browser console:
```javascript
window.collectedTweets = {};
```

### 6. Batch Collection Loop

Run this script repeatedly until `newThisBatch` returns 0 twice in a row:

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
    if (id && !window.collectedTweets[id] && (!window.existingIds || !window.existingIds.has(id))) {
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

**Between each run:**
- Wait 2-3 seconds
- Check `newThisBatch` value
- If 0 twice in a row, collection is complete

### 7. Export Collected Tweets

When done, run in browser console:
```javascript
JSON.stringify(Object.values(window.collectedTweets))
```

Copy the output (JSON array).

### 8. Save to Storage

Option A: Save from JSON string
```bash
python scripts/twitter_collect.py save HANDLE_HERE --data '[{"id":"123",...}]'
```

Option B: Save from temp file
```bash
# First save JSON to file
echo '[...]' > /tmp/tweets.json
python scripts/twitter_collect.py save HANDLE_HERE --file /tmp/tweets.json
```

### 9. Verify Collection

```bash
python scripts/twitter_collect.py coverage HANDLE_HERE
```

## Rate Limit Guidelines

| Constraint | Limit |
|------------|-------|
| Tweets per scroll | 15-20 max |
| Delay between scrolls | 2-3 seconds |
| Tweets per 15-min session | 200-300 |
| If rate limited | Pause 5 minutes |

## Session Planning

For accounts with many tweets, plan multiple sessions:

| Session | Period | Expected |
|---------|--------|----------|
| Day 1 | Q4 2024 (Oct-Dec) | ~300 tweets |
| Day 2 | Q3 2024 (Jul-Sep) | ~300 tweets |
| Day 3 | Q2 2024 (Apr-Jun) | ~300 tweets |
| Day 4 | Q1 2024 (Jan-Mar) | ~300 tweets |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Something went wrong" | Click Retry or reload page |
| No tweets loading | Check if logged in to Twitter |
| Rate limit hit | Wait 15 minutes |
| Duplicate tweets | Handled by save script |
| Page frozen | Refresh and continue from last date |

## Full Collection Workflow Example

```
1. Run: python scripts/twitter_collect.py coverage vildkatten
   -> Shows gaps in 2024

2. Run: python scripts/twitter_collect.py ids vildkatten
   -> Copy existing IDs

3. Run: python scripts/twitter_collect.py url vildkatten --since 2024-10-01 --until 2024-12-31
   -> Get URL: https://x.com/search?q=from:vildkatten...

4. Navigate to URL in browser

5. In console: window.existingIds = new Set([...]);
              window.collectedTweets = {};

6. Run collection script repeatedly (15-20 times)
   -> Each run: wait 2-3 sec, check newThisBatch

7. When newThisBatch=0 twice:
   -> Run: JSON.stringify(Object.values(window.collectedTweets))
   -> Copy output

8. Run: python scripts/twitter_collect.py save vildkatten --data '[...]'

9. Verify: python scripts/twitter_collect.py coverage vildkatten
```

## Storage Location

Tweets saved to: `data/twitter/raw/HANDLE_HERE/tweets.jsonl`

Same format as API method - one JSON object per line.
