# Twitter Tweet Collection

Collect tweets from a Twitter/X account using browser automation.

## Arguments
- `$ARGUMENTS` - Twitter handle and optional date range (e.g., "vildkatten" or "vildkatten 2024-04")

## Prerequisites
- User must be logged into Twitter/X in their browser
- MCP browser tools must be available

## Workflow

### Step 1: Analyze Coverage
First, check what tweets are already collected:

```bash
python scripts/twitter_collect.py coverage {handle}
```

This shows:
- Complete months (20+ tweets)
- Incomplete months (< 20 tweets)
- Missing months (no tweets)

### Step 2: Get Existing IDs for Deduplication
Load existing tweet IDs to avoid downloading duplicates:

```bash
python scripts/twitter_collect.py ids {handle}
```

Store this in the browser before collection:
```javascript
window.existingIds = new Set([...]);  // Paste IDs here
```

### Step 3: Navigate to Search URL
Generate the search URL for the target period:

```bash
python scripts/twitter_collect.py url {handle} --since {YYYY-MM-DD} --until {YYYY-MM-DD}
```

Navigate to the URL in the browser.

### Step 4: Initialize Collection
In the browser, run:
```javascript
window.collectedTweets = {};
```

### Step 5: Batch Collection Loop
Run this JavaScript repeatedly until `newThisBatch` returns 0 twice in a row:

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

**Rate Limit Guidelines:**
- Wait 2-3 seconds between scrolls
- Max ~200-300 tweets per 15-minute session
- If "rate limit exceeded" appears, pause 5 minutes

### Step 6: Export and Save
When collection is complete (newThisBatch=0 twice), export the tweets:

```javascript
JSON.stringify(Object.values(window.collectedTweets))
```

Save to file and run:
```bash
python scripts/twitter_collect.py save {handle} --data '{json_data}'
```

Or save to a temp file and:
```bash
python scripts/twitter_collect.py save {handle} --file /tmp/tweets.json
```

### Step 7: Verify
Check the updated coverage:
```bash
python scripts/twitter_collect.py coverage {handle}
```

## Rate Limit Strategy

For free Twitter accounts (~1000 posts/day):

| Session | Period | Expected Tweets |
|---------|--------|-----------------|
| Day 1 | Q4 2024 | ~300 |
| Day 2 | Q3 2024 | ~300 |
| Day 3 | Q2 2024 | ~300 |
| Day 4 | Q1 2024 | ~300 |

Within each session:
- Max 15-20 tweets per scroll
- 2-3 sec delay between scrolls
- Pause 5 min if rate limit hit
- Max 200-300 tweets per 15-min window

## Troubleshooting

**"Something went wrong" error:**
Click the Retry button or reload the page.

**No tweets loading:**
Check if logged in. Twitter requires login for advanced search.

**Rate limit hit:**
Wait 15 minutes, then continue.

**Duplicate tweets:**
Already handled by deduplication in save script.
