# PodStock – Claude Code Instructions

**Version:** 2.0
**Datum:** 2025-12-27

---

## 🎯 Purpose of This Document

Detta dokument är **den primära guiden** för Claude Code när du arbetar på PodStock-projektet. Läs detta dokument FÖRST innan du gör något annat.

---

## 📋 Quick Reference

| Document | Purpose |
|----------|---------|
| `PRD.md` | Vad ska byggas och varför |
| `ARCHITECTURE.md` | Hur systemet är strukturerat |
| `IMPLEMENTATION.md` | **Checklista** - uppdatera denna löpande! |
| `CONVENTIONS.md` | Kodstil och best practices |
| `CLAUDE_CODE_INSTRUCTIONS.md` | Detta dokument - hur du ska arbeta |

---

## 🔌 BEFINTLIGA KAPABILITETER - LÄS DETTA FÖRST!

> **VIKTIGT:** Projektet har växt långt förbi MVP. Innan du använder WebSearch eller externa verktyg,
> kontrollera om funktionaliteten redan finns nedan. Detta sparar tid och ger bättre resultat.

### A. PRISDATA (Yahoo Finance) - ANVÄND ISTÄLLET FÖR WEBSEARCH

```python
from podstock.prices.clients.yahoo import YahooFinanceClient
from datetime import datetime

client = YahooFinanceClient()

# Aktuell kurs
snapshot = client.get_current_price("EVO.ST")  # → PriceSnapshot(price=1234.50, currency="SEK")

# Historisk kurs (hanterar helger automatiskt)
hist = client.get_historical_price("EVO.ST", datetime(2025, 6, 15))

# Kursintervall
prices = client.get_price_range("EVO.ST", start_date, end_date)

# Krypto
btc = client.get_current_price("BTC-USD")
```

**Marknader:** `.ST` (Sverige), `.HE` (Finland), `.CO` (Danmark), `.OL` (Norge), `-USD` (krypto)

**CLI:**
```bash
podstock prices verify --today          # Verifiera alla spårade rekommendationer
podstock prices list                    # Lista spårade rekommendationer
podstock prices accuracy --podcast X    # Träffsäkerhetsstatistik
```

### B. TICKER-MAPPNING (Bolagsnamn → Ticker)

```python
from pathlib import Path
from podstock.prices import TickerMapper

mapper = TickerMapper(Path("data/prices/ticker_mapping.json"))
ticker = mapper.lookup("Evolution")      # → "EVO.ST"
ticker = mapper.lookup("Hacksaw Gaming") # → "HACK.ST"
```

**Fil:** `data/prices/ticker_mapping.json` (innehåller 100+ mappningar)

**CLI:**
```bash
podstock prices mapping search "evol"   # Fuzzy-sökning
podstock prices mapping list            # Alla mappningar
podstock prices mapping add "Bolag" "TICKER.ST"
```

### C. EXTRAHERADE REKOMMENDATIONER

**All podcast-data finns redan extraherad:**
- **Plats:** `data/extracted/glm-batch/*.json`
- **Format:** `EpisodeAnalysis` med `recommendations[]`, `stocks_discussed[]`, `key_takeaways[]`
- **Podcasts:** veckanstrade, marketmakers, borsmagasinet, gotttjot, marknaden, m.fl.

```python
import json
from pathlib import Path

# Läs en specifik analys
with open("data/extracted/glm-batch/veckanstrade-2025-09-10-3178.json") as f:
    analysis = json.load(f)
    for rec in analysis["recommendations"]:
        print(f"{rec['stock_name']}: {rec['action']} - {rec['reasoning']}")
```

**CLI:**
```bash
podstock extract search --stock "Evolution"
podstock extract search --speaker "Gilmore"
podstock extract search --action buy
```

### D. SQLite-DATABAS

**Fil:** `data/podstock.db` (96 MB, 15+ tabeller)

```python
from podstock.db.engine import get_session
from podstock.db.models import Recommendation, Security

with get_session() as session:
    recs = session.query(Recommendation).filter(
        Recommendation.action == "buy"
    ).all()
```

**Tabeller:** `sources`, `content`, `analyses`, `securities`, `recommendations`, `mentions`, `prices`, `unified_signals`

**CLI:**
```bash
podstock db search "Evolution" --action buy
podstock db status
```

### E. TWITTER-DATA

**Plats:** `data/twitter/raw/*/tweets.jsonl`

```python
from podstock.twitter.storage import TweetStorage
storage = TweetStorage(Path("data"))
for tweet in storage.load_tweets("vildkatten", limit=100):
    print(tweet.text, tweet.mentioned_tickers)
```

**CLI:**
```bash
podstock twitter search --query "Evolution"
podstock twitter list
```

### F. KRYPTOPRIS (CoinGecko)

```python
from podstock.crypto.coingecko import CoinGeckoClient
client = CoinGeckoClient()
price = client.get_current_price("BTC", "USD")
hist = client.get_historical_price("ETH", datetime(2025, 1, 15), "USD")
```

**Stödjer:** BTC, ETH, SOL, XRP, ADA, DOGE, DOT, AVAX, LINK, MATIC + 20 till

---

## ⛔ ANVÄND ALDRIG WEBSEARCH FÖR

| Behov | Använd istället |
|-------|-----------------|
| Aktiekurser | `YahooFinanceClient` |
| Kryptokurser | `CoinGeckoClient` eller `YahooFinanceClient` (BTC-USD) |
| Ticker-uppslag | `TickerMapper` + `data/prices/ticker_mapping.json` |
| Podcast-rekommendationer | `data/extracted/glm-batch/*.json` |
| Historiska rekommendationer | SQLite: `podstock db search` |
| Twitter-analys | `data/twitter/` + `podstock twitter` |
| Bolagsfilings | `podstock filings` (SEC EDGAR, Svenska IR) |

---

## 🔴 KRITISKA REGLER

### 1. Uppdatera IMPLEMENTATION.md efter varje uppgift
```markdown
# Efter att du implementerat något:
1. Öppna IMPLEMENTATION.md
2. Checka av relevanta punkter: [ ] → [x]
3. Lägg till datum
4. Notera eventuella avvikelser eller beslut
```

### 2. Skriv tester INNAN eller TILLSAMMANS med kod
```markdown
# Test-Driven Development (TDD) flow:
1. Skriv ett failing test
2. Implementera minimal kod för att passa testet
3. Refaktorera
4. Repeat
```

### 3. Commita ofta med tydliga meddelanden
```markdown
# Commit efter varje logisk enhet:
- En funktion implementerad
- Ett test tillagt
- En bug fixad

# Exempel:
feat(rss): implement fetch_feed function
test(rss): add tests for parse_episode
fix(download): handle timeout correctly
```

### 4. Fråga vid osäkerhet
```markdown
# Om något är oklart:
1. Dokumentera frågan i IMPLEMENTATION.md under "Blockers & Open Questions"
2. Gör ett rimligt antagande och dokumentera det
3. Fortsätt med nästa uppgift om möjligt
```

---

## 🚀 Hur du startar ett nytt arbetspass

### Steg 1: Orientera dig
```bash
# Läs igenom nuvarande status
cat IMPLEMENTATION.md | head -100

# Se vad som är klart och vad som är nästa
grep -n "\[ \]" IMPLEMENTATION.md | head -20
```

### Steg 2: Välj nästa uppgift
```markdown
Prioriteringsordning:
1. Phase 0 (Setup) måste vara klart först
2. Phase 1 (Core) innan Phase 2-5
3. Phase 6 (CLI) kan påbörjas parallellt med Phase 2-5
4. Följ fasordningen inom varje fas

Om något är blockerat:
- Dokumentera i IMPLEMENTATION.md
- Hoppa till nästa oberoende uppgift
```

### Steg 3: Implementera
```markdown
För varje uppgift:
1. Läs relevant sektion i ARCHITECTURE.md
2. Skriv test först (eller parallellt)
3. Implementera kod
4. Kör tester: pytest tests/
5. Kör linter: ruff check src/
6. Kör type check: mypy src/
7. Commita
8. Uppdatera IMPLEMENTATION.md
```

---

## 📁 Filskapande - Steg för steg

### När du skapar en ny modul:

```python
# 1. Skapa filen med rätt header
"""Module description.

This module provides...
"""

from __future__ import annotations

# 2. Lägg till i __init__.py för modulen
# src/podstock/rss/__init__.py
from podstock.rss.parser import fetch_feed, parse_episode

# 3. Skapa motsvarande testfil
# tests/test_rss_parser.py

# 4. Uppdatera IMPLEMENTATION.md
```

### Aktuell mappstruktur (2025):

```
src/podstock/
├── __init__.py              # Version, public API
├── __main__.py              # Entry: python -m podstock
├── cli.py                   # Huvudsakliga CLI-kommandon
│
├── core/                    # Kärnfunktionalitet
│   ├── config.py            # Konfigurationshantering
│   ├── models.py            # Podcast, Episode, Recommendation
│   ├── state.py             # Processläge (JSON-baserat)
│   └── exceptions.py
│
├── prices/                  # 💰 PRISDATA - Yahoo Finance
│   ├── clients/
│   │   ├── yahoo.py         # YahooFinanceClient
│   │   └── coingecko.py     # CoinGecko-adapter
│   ├── tracker.py           # PriceTracker - rekommendationsspårning
│   ├── ticker_mapping.py    # TickerMapper - namn→ticker
│   ├── storage.py           # JSONL-lagring
│   └── models.py            # PriceSnapshot, TrackedRecommendation
│
├── crypto/                  # 🪙 KRYPTOANALYS
│   ├── coingecko.py         # CoinGeckoClient med caching
│   ├── analyzer.py          # Sentimentanalys
│   └── price_tracker.py     # Kryptoprisspårning
│
├── twitter/                 # 🐦 TWITTER-INTEGRATION
│   ├── api_client.py        # TwitterAPIClient (twitterapi.io)
│   ├── storage.py           # TweetStorage
│   ├── analyze.py           # Aktieomnämnanden
│   └── models.py            # Tweet, TwitterSource
│
├── youtube/                 # 📺 YOUTUBE-TRANSKRIPT
│   ├── extractor.py         # YouTubeExtractor (yt-dlp)
│   └── storage.py
│
├── filings/                 # 📄 BOLAGSRAPPORTER
│   ├── clients/
│   │   └── edgar.py         # SEC EDGAR (US)
│   ├── swedish/
│   │   └── ir_scraper.py    # Svenska IR-sidor
│   └── models.py            # Filing, Company
│
├── earnings/                # 📊 EARNINGS CALLS
│   └── playwright_scraper.py # Inderes.fi/se scraping
│
├── news/                    # 📰 NYHETSFLÖDEN
│   └── feeds.py             # RSS-nyhetsaggregering
│
├── unified/                 # 🔗 KORSKÖLLA-AGGREGERING
│   ├── models.py            # UnifiedSignal
│   ├── search.py            # SignalSearcher
│   └── enrichment.py        # Prisanrikning
│
├── db/                      # 🗄️ SQLITE-DATABAS
│   ├── engine.py            # SQLAlchemy setup
│   ├── models.py            # ORM-modeller
│   ├── loader.py            # JSON→SQLite import
│   └── performance.py       # Avkastningsberäkning
│
├── extract/                 # 🤖 LLM-EXTRAKTION
│   ├── llm_client.py        # Claude/Ollama-klienter
│   ├── models.py            # EpisodeAnalysis, StockRecommendation
│   └── prompt_templates.py
│
├── rss/                     # 🎙️ PODCAST RSS
│   ├── parser.py            # RSS-parsning
│   └── downloader.py        # MP3-nedladdning
│
├── sync/                    # 🔄 PIPELINE-ORKESTRERING
│   └── orchestrator.py      # Download→Transcribe→Extract
│
├── transcribe/              # 🎤 TRANSKRIBERING
│   ├── whisper.py           # mlx-whisper (Apple Silicon)
│   └── apple.py             # Apple Podcasts-extraktion
│
└── report/                  # 📝 RAPPORTGENERERING
    └── markdown.py

data/                        # All data (gitignored förutom config)
├── podstock.db              # SQLite-databas (96 MB)
├── config.json              # Global konfiguration
├── state.json               # Processläge
├── podcasts.json            # Podcast-konfiguration
├── prices/
│   ├── ticker_mapping.json  # 💡 Bolagsnamn → Ticker
│   └── verified_recommendations.jsonl
├── extracted/
│   └── glm-batch/           # 💡 Alla extraherade rekommendationer
│       └── *.json
├── twitter/
│   ├── sources.json
│   └── raw/*/tweets.jsonl   # 💡 Alla tweets
├── youtube/
├── filings/
├── earnings/
└── news/
```

---

## 🧪 Testning

### Köra tester
```bash
# Alla tester
pytest tests/

# Med coverage
pytest tests/ --cov=src/podstock --cov-report=term-missing

# Specifik testfil
pytest tests/test_rss_parser.py

# Specifikt test
pytest tests/test_rss_parser.py::TestFetchFeed::test_handles_timeout
```

### Testfil-template
```python
"""Tests for podstock.rss.parser module."""

import pytest
from pathlib import Path

from podstock.rss.parser import fetch_feed, parse_episode
from podstock.core.models import Episode
from podstock.core.exceptions import RSSError


@pytest.fixture
def sample_rss_path() -> Path:
    """Path to sample RSS fixture."""
    return Path(__file__).parent / "fixtures" / "sample_rss_libsyn.xml"


@pytest.fixture
def sample_rss_content(sample_rss_path: Path) -> str:
    """Content of sample RSS."""
    return sample_rss_path.read_text()


class TestParseEpisode:
    """Tests for parse_episode function."""
    
    def test_extracts_title(self, sample_rss_content):
        """Should extract episode title from RSS item."""
        # Arrange
        # ... parse RSS to get item
        
        # Act
        episode = parse_episode(item)
        
        # Assert
        assert episode.title == "Avsnitt 598 - Julspecial"
    
    def test_handles_missing_optional_fields(self):
        """Should handle missing optional fields gracefully."""
        ...
```

---

## 🔧 Vanliga uppgifter

### Lägga till en ny podcast i config

```json
// data/podcasts.json
{
  "podcasts": [
    {
      "id": "borspodden",
      "name": "Börspodden",
      "rss_url": "https://borspodden.libsyn.com/rss",
      "hosts": ["Johan Isaksson", "John Skogman"]
    },
    // ... etc
  ]
}
```

### Skapa pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "podstock"
version = "0.1.0"
description = "Track stock recommendations from Swedish podcasts"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "feedparser>=6.0.0",
    "requests>=2.28.0",
    "pydantic>=2.0.0",
    "rich>=13.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov",
    "ruff",
    "mypy",
]
transcribe = [
    "mlx-whisper>=0.1.0",
]

[project.scripts]
podstock = "podstock.cli:main"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.mypy]
python_version = "3.11"
strict = true
```

### Skapa requirements.txt

```
# Core
feedparser>=6.0.0
requests>=2.28.0
pydantic>=2.0.0
rich>=13.0.0

# Transcription (optional, install separately on M4 Mac)
# mlx-whisper>=0.1.0

# Development
pytest>=7.0.0
pytest-cov
ruff
mypy
```

---

## 🐛 Debugging

### Vanliga problem

**Problem: mlx-whisper fungerar inte**
```bash
# Verifiera M4/Apple Silicon
python -c "import platform; print(platform.processor())"

# Installera korrekt
pip install mlx-whisper

# Test
python -c "import mlx_whisper; print('OK')"
```

**Problem: RSS parsing misslyckas**
```python
# Debug med feedparser direkt
import feedparser
feed = feedparser.parse("https://borspodden.libsyn.com/rss")
print(feed.bozo)  # True = parsing error
print(feed.bozo_exception)  # Error details
```

**Problem: Tester hittar inte moduler**
```bash
# Installera i utvecklingsläge
pip install -e .

# Eller kör med python path
PYTHONPATH=src pytest tests/
```

---

## 📝 Templates

### Ny funktion template
```python
def function_name(
    required_arg: ArgType,
    optional_arg: ArgType | None = None,
    *,
    keyword_only: bool = False,
) -> ReturnType:
    """One-line description.
    
    Longer description if needed.
    
    Args:
        required_arg: Description.
        optional_arg: Description. Defaults to None.
        keyword_only: Description. Defaults to False.
    
    Returns:
        Description of return value.
    
    Raises:
        SpecificError: When this happens.
    
    Example:
        >>> result = function_name("input")
        >>> print(result)
    """
    # Validate input
    if not required_arg:
        raise ValueError("required_arg cannot be empty")
    
    # Main logic
    ...
    
    return result
```

### Ny klass template
```python
class ClassName:
    """One-line description.
    
    Longer description if needed.
    
    Attributes:
        attr1: Description.
        attr2: Description.
    
    Example:
        >>> obj = ClassName(config)
        >>> obj.do_something()
    """
    
    # Class constants
    DEFAULT_VALUE = 42
    
    def __init__(self, config: Config) -> None:
        """Initialize ClassName.
        
        Args:
            config: Application configuration.
        """
        self._config = config
        self._state: dict[str, Any] = {}
    
    def public_method(self) -> None:
        """Do something publicly visible."""
        self._private_helper()
    
    def _private_helper(self) -> None:
        """Internal helper method."""
        ...
    
    @property
    def some_property(self) -> str:
        """Description of property."""
        return self._state.get("key", "default")
```

---

## ✅ Checklista innan du avslutar ett arbetspass

```markdown
□ Alla nya filer har docstrings
□ Alla publika funktioner har type hints
□ Tester skrivna och passerar
□ ruff check visar inga errors
□ mypy visar inga errors (eller dokumenterade ignores)
□ IMPLEMENTATION.md uppdaterad
□ Alla ändringar committade
□ Commit messages följer konventionen
```

---

## 🆘 Om du kör fast

1. **Läs om relevant dokumentation** - PRD.md, ARCHITECTURE.md
2. **Kolla CONVENTIONS.md** för kodstil
3. **Dokumentera problemet** i IMPLEMENTATION.md under "Blockers"
4. **Gör ett antagande** och fortsätt - dokumentera antagandet
5. **Fråga användaren** om något är fundamentalt oklart

---

## 🎯 Projektstatus (2025)

Projektet har passerat MVP och är nu ett fullfjädrat system för aktieanalys.

### ✅ Implementerat och fungerande

| Funktion | Status | CLI-kommando |
|----------|--------|--------------|
| Podcast-synkronisering | ✅ Klart | `podstock sync` |
| Transkribering (Whisper) | ✅ Klart | `podstock transcribe` |
| Transkribering (Apple Podcasts) | ✅ Klart | Via `podstock sync` |
| LLM-extraktion | ✅ Klart | `podstock extract` |
| Prisverifiering (Yahoo Finance) | ✅ Klart | `podstock prices verify` |
| Ticker-mappning | ✅ Klart | `podstock prices mapping` |
| Twitter-integration | ✅ Klart | `podstock twitter` |
| YouTube-transkript | ✅ Klart | `podstock youtube` |
| Kryptoanalys (CoinGecko) | ✅ Klart | Via prismodulen |
| SQLite-databas | ✅ Klart | `podstock db` |
| Unified signals | ✅ Klart | `podstock unified` |
| SEC EDGAR filings | ✅ Klart | `podstock filings` |
| Svenska IR-scraping | ✅ Klart | `podstock filings` |
| Earnings calls (Inderes) | ✅ Klart | `podstock earnings` |
| Nyhetsflöden (RSS) | ✅ Klart | `podstock news` |

### 📊 Data i systemet

- **7+ podcasts** konfigurerade (Market Makers, Veckans Trade, Börspodden, m.fl.)
- **300+ avsnitt** transkriberade och analyserade
- **1000+ rekommendationer** extraherade
- **100+ ticker-mappningar** i `data/prices/ticker_mapping.json`
- **SQLite-databas** på 96 MB med 15+ tabeller

### 🔧 Vanliga arbetsflöden

```bash
# Synka och analysera ny podcast
podstock sync --podcast veckanstrade --limit 5

# Hämta aktuella priser för alla rekommendationer
podstock prices verify --today

# Sök efter specifikt bolag i all data
podstock db search "Evolution"

# Lista alla köprekar från en podcast
podstock db search --podcast marketmakers --action buy

# Visa träffsäkerhetsstatistik
podstock prices accuracy --podcast veckanstrade
```

---

**Dokumentet uppdaterat: 2025-12-27**
