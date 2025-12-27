# Twitter Module

Samlar och analyserar tweets från svenska finansprofiler.

## Syfte

- Samla tweets från utvalda finansprofiler
- Extrahera aktierekommendationer med LLM
- Spåra sentiment och trender över tid

## Komponenter

### 1. Tweet Collection

```python
from podstock.twitter.api_collector import TwitterAPICollector

collector = TwitterAPICollector(api_key="...")
tweets = collector.collect_user_tweets(
    source_id="matematikern",
    since_date="2024-01-01",
)
```

### 2. Tweet Analysis

```python
from podstock.twitter.analyze import TweetAnalyzer
from podstock.analysis import create_llm_client

client = create_llm_client("claude-sonnet-4-20250514")
analyzer = TweetAnalyzer(client)

# Analysera tweets
analyses = analyzer.analyze_tweets(tweets)

# Spara
analyzer.save_analyses(analyses, Path("data/twitter/analysis/"), "matematikern")
```

## Datamodeller

### Tweet

Representerar en enskild tweet:

```python
class Tweet(BaseModel):
    id: str
    source_id: str
    author_handle: str
    text: str
    posted_at: datetime

    is_retweet: bool
    is_reply: bool
    is_quote: bool

    likes: int | None
    retweets: int | None

    mentioned_tickers: list[str]  # Extraherade $TICKER
    mentioned_users: list[str]    # Extraherade @user
    hashtags: list[str]           # Extraherade #hashtag

    def extract_entities(self) -> dict:
        """Extrahera tickers, mentions, hashtags."""
```

### TweetAnalysis

LLM-genererad analys av en tweet:

```python
class TweetAnalysis(BaseModel):
    tweet_id: str
    source_id: str

    stock_mentions: list[StockMention]
    market_sentiment: Literal["bullish", "bearish", "neutral", "mixed"]

    is_actionable: bool
    is_speculation: bool
    has_price_target: bool

    model_used: str
    processed_at: datetime
```

### StockMention

```python
class StockMention(BaseModel):
    stock_name: str
    ticker: str | None
    action: TweetActionType  # BUY, SELL, HOLD, WATCH, AVOID, UNKNOWN
    confidence: Literal["high", "medium", "low", "speculative"]
    reasoning: str | None
    quote: str
```

### TweetActionType

```python
class TweetActionType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    WATCH = "watch"
    AVOID = "avoid"
    UNKNOWN = "unknown"
```

## Filer

| Fil | Beskrivning |
|-----|-------------|
| `models.py` | Tweet, TweetAnalysis, TwitterSource |
| `analyze.py` | TweetAnalyzer med LLM-integration |
| `api_collector.py` | Twitter API integration |
| `storage.py` | Tweet-lagring (JSON) |
| `search.py` | Sökfunktioner |

## CLI-kommandon

```bash
# Lägg till källa
podstock twitter add matematikern --handle @Matematikern3

# Samla tweets
podstock twitter collect matematikern --since 2024-01-01

# Analysera
podstock twitter analyze matematikern
```

## Lagring

- `data/twitter/raw/{source_id}/` - Råa tweets (JSON)
- `data/twitter/analysis/` - Analyserade tweets
- `data/twitter_sources.json` - Konfigurerade källor
- `data/twitter_state.json` - Collection state

## Konfiguration

Twitter-källor konfigureras i `data/twitter_sources.json`:

```json
{
  "sources": [
    {
      "id": "matematikern",
      "handle": "Matematikern3",
      "display_name": "Matematikern",
      "category": "analyst",
      "language": "sv",
      "active": true
    }
  ]
}
```

## Se även

- `docs/ANALYSIS-GUIDE.md` - Arkitekturdokumentation
- `unified/importers/twitter.py` - Import till unified signals
