# Crypto Module

Analyserar krypto-sentiment från YouTube-transkript och andra källor.

## Syfte

Extrahera strukturerad sentiment-data för kryptovalutor från video-transkript:

- Bitcoin/altcoin sentiment (very_bullish → very_bearish)
- Prisprediktion och targets
- Bull/bear case för varje asset
- Market outlook och dominans-trender

## Användning

```python
from podstock.crypto.analyzer import CryptoAnalyzer
from podstock.analysis import create_llm_client

# Skapa analyzer
client = create_llm_client("claude-sonnet-4-20250514")
analyzer = CryptoAnalyzer(client)

# Analysera transkript
analysis = analyzer.analyze_transcript(
    transcript_path=Path("data/youtube/transcripts/technical-roundup/abc123.txt"),
    source_type="youtube",
    channel_name="Technical Roundup",
)

# Spara
analyzer.save_analysis(analysis, Path("data/crypto/analyses/"))
```

## Datamodeller

### CryptoSentimentAnalysis

Huvudmodell för analysresultat:

```python
class CryptoSentimentAnalysis(BaseModel):
    source_id: str
    source_type: Literal["youtube", "podcast", "twitter"]
    channel_or_podcast: str
    date: str

    speakers: list[str]
    main_topics: list[str]
    assets_discussed: list[str]

    mentions: list[CryptoMention]

    overall_market_sentiment: SentimentLevel
    bitcoin_dominance_view: Literal["increasing", "decreasing", "stable"]
    alt_season_prediction: bool | None

    summary: str
    key_takeaways: list[str]
```

### CryptoMention

Enskild krypto-mention med sentiment:

```python
class CryptoMention(BaseModel):
    asset_name: str          # "Bitcoin"
    asset_symbol: str        # "BTC"
    sentiment: SentimentLevel
    confidence: Literal["high", "medium", "low", "speculative"]
    quote: str
    reasoning: str
    price_target: float | None
    time_horizon: str | None
    mentioned_catalysts: list[str]
    risk_factors_mentioned: list[str]
```

### SentimentLevel

```python
class SentimentLevel(str, Enum):
    VERY_BULLISH = "very_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    VERY_BEARISH = "very_bearish"
```

## Filer

| Fil | Beskrivning |
|-----|-------------|
| `models.py` | Pydantic-modeller för crypto-analys |
| `analyzer.py` | CryptoAnalyzer med LLM-integration |
| `prompt_templates.py` | System/user prompts för extraktion |

## Lagring

Analysresultat sparas i:
- `data/crypto/analyses/` - Analyserad sentiment per källa

## Se även

- `docs/ANALYSIS-GUIDE.md` - Arkitekturdokumentation
- `youtube/` - YouTube-transkript extraktion
