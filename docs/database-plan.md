# PodStock SQLite Database Plan

> Version: 1.0
> Datum: 2025-12-26
> Status: Godkänd för implementation

## 1. Översikt

### Syfte
SQLite-databas som frågelager över analyserad data från podcasts, tweets och andra källor.

### Principer
- **JSON är source of truth** — databasen kan regenereras
- **Upsert med content hash** — idempotent, skapar endast ny version vid faktisk ändring
- **Versionering** — analyshistorik sparas
- **Extensibel** — lätt att lägga till nya content-typer

### Datastorlek (uppskattad)
| Tabell | År 1 | År 5 |
|--------|------|------|
| content | ~600 | ~1500 |
| analyses | ~1200 | ~3000 |
| recommendations | ~6000 | ~15000 |
| prices | ~100k | ~500k |

---

## 2. Mappstruktur

```
src/podstock/
├── db/
│   ├── __init__.py           # Exporterar publika funktioner
│   ├── engine.py             # get_engine(), get_session(), init_db()
│   ├── models.py             # SQLAlchemy ORM-modeller
│   ├── schema.sql            # Ren SQL (referens)
│   ├── loader.py             # BaseLoader, PodcastLoader, TwitterLoader
│   ├── queries.py            # Vanliga sökfunktioner
│   ├── ticker_lookup.py      # resolve_ticker(), seed_securities()
│   └── cli.py                # CLI-kommandon

data/
├── podstock.db               # SQLite (gitignore)
├── extracted/                # JSON source of truth
├── prices/
│   └── ticker_mapping.json   # Befintlig mapping (~150 aktier)
└── ...
```

---

## 3. Databasschema

### 3.1 Core Tables

```sql
-- Aktivera foreign keys (krävs vid varje connection)
PRAGMA foreign_keys = ON;

-- Innehållskällor (podcasts, twitter-konton, youtube-kanaler)
CREATE TABLE sources (
    id              TEXT PRIMARY KEY,      -- 'fillorkill', 'vildkatten'
    type            TEXT NOT NULL,         -- 'podcast', 'twitter', 'youtube'
    name            TEXT NOT NULL,         -- 'Fill or Kill'
    description     TEXT,
    language        TEXT DEFAULT 'sv',
    metadata        TEXT,                  -- JSON
    active          INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Allt innehåll (episodes, tweets, videos)
CREATE TABLE content (
    id              TEXT PRIMARY KEY,      -- 'fillorkill-2025-12-23-cf58'
    source_id       TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    type            TEXT NOT NULL,         -- 'episode', 'tweet', 'video'
    external_id     TEXT,                  -- tweet_id, video_id, guid
    title           TEXT,
    published_at    TEXT NOT NULL,
    raw_text        TEXT,
    word_count      INTEGER,
    duration_seconds INTEGER,
    metadata        TEXT,                  -- JSON
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_content_source ON content(source_id);
CREATE INDEX idx_content_published ON content(published_at);
CREATE INDEX idx_content_type ON content(type);

-- Versionerade analyser
CREATE TABLE analyses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id      TEXT NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    version         INTEGER NOT NULL DEFAULT 1,
    content_hash    TEXT,                  -- SHA256 för idempotens
    model_used      TEXT,
    analyzed_at     TEXT NOT NULL,
    summary         TEXT,
    sentiment       TEXT,                  -- 'bullish', 'bearish', 'neutral'
    raw_json        TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(content_id, version)
);

CREATE INDEX idx_analyses_content ON analyses(content_id);
CREATE INDEX idx_analyses_hash ON analyses(content_hash);

-- View för senaste version
CREATE VIEW current_analyses AS
SELECT * FROM analyses a1
WHERE version = (
    SELECT MAX(version) FROM analyses a2
    WHERE a2.content_id = a1.content_id
);
```

### 3.2 Securities & Ticker Lookup

```sql
-- Värdepapper/aktier
CREATE TABLE securities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,         -- 'EVO.ST', 'AAPL'
    name            TEXT NOT NULL,         -- 'Evolution', 'Apple'
    exchange        TEXT,                  -- 'OMX', 'NYSE', 'LSE'
    market          TEXT,                  -- 'sweden', 'usa', 'europe'
    currency        TEXT,                  -- 'SEK', 'USD'
    isin            TEXT,
    sector          TEXT,
    asset_type      TEXT DEFAULT 'stock',  -- 'stock', 'crypto'
    status          TEXT DEFAULT 'active', -- 'active', 'delisted'
    delisted_date   TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(ticker, exchange)
);

CREATE INDEX idx_securities_ticker ON securities(ticker);
CREATE INDEX idx_securities_name ON securities(name);

-- Alternativa namn för lookup
CREATE TABLE security_aliases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    security_id     INTEGER NOT NULL REFERENCES securities(id) ON DELETE CASCADE,
    alias           TEXT NOT NULL,
    alias_type      TEXT DEFAULT 'name',   -- 'name', 'ticker_variant', 'twitter'

    UNIQUE(alias)
);

CREATE INDEX idx_aliases_alias ON security_aliases(alias);

-- Relationer mellan samma bolag på olika börser
CREATE TABLE security_relations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    primary_id      INTEGER NOT NULL REFERENCES securities(id),
    related_id      INTEGER NOT NULL REFERENCES securities(id),
    relation_type   TEXT,                  -- 'same_company', 'adr', 'dual_listing'

    UNIQUE(primary_id, related_id)
);

-- Omatchade aktier för manuell granskning
CREATE TABLE pending_securities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_name        TEXT NOT NULL,
    raw_ticker      TEXT,
    source          TEXT,
    context         TEXT,
    occurrence_count INTEGER DEFAULT 1,
    status          TEXT DEFAULT 'pending', -- 'pending', 'resolved', 'rejected'
    resolved_security_id INTEGER REFERENCES securities(id),
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(raw_name, raw_ticker)
);
```

### 3.3 Recommendations & Mentions

```sql
-- Rekommendationer (tydliga köp/sälj-signaler)
CREATE TABLE recommendations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id     INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    security_id     INTEGER REFERENCES securities(id) ON DELETE SET NULL,
    raw_stock_name  TEXT NOT NULL,
    raw_ticker      TEXT,
    action          TEXT NOT NULL,         -- 'buy', 'sell', 'hold', 'watch', 'avoid'
    confidence      TEXT,                  -- 'high', 'medium', 'low'
    speaker         TEXT,
    speaker_role    TEXT,
    reasoning       TEXT,
    quote           TEXT,
    timestamp       TEXT,
    price_target    TEXT,
    time_horizon    TEXT,
    sector          TEXT,
    market          TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rec_analysis ON recommendations(analysis_id);
CREATE INDEX idx_rec_security ON recommendations(security_id);
CREATE INDEX idx_rec_action ON recommendations(action);
CREATE INDEX idx_rec_unmatched ON recommendations(raw_stock_name)
    WHERE security_id IS NULL;

-- Omnämnanden (utan tydlig signal)
CREATE TABLE mentions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id     INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    security_id     INTEGER REFERENCES securities(id) ON DELETE SET NULL,
    raw_stock_name  TEXT NOT NULL,
    raw_ticker      TEXT,
    sentiment       TEXT,                  -- 'positive', 'negative', 'neutral'
    context         TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_mentions_analysis ON mentions(analysis_id);
CREATE INDEX idx_mentions_security ON mentions(security_id);

-- Key takeaways
CREATE TABLE key_takeaways (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id     INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    takeaway        TEXT NOT NULL,
    sort_order      INTEGER DEFAULT 0
);
```

### 3.4 Prices & Performance

```sql
-- Historisk prisdata
CREATE TABLE prices (
    security_id     INTEGER NOT NULL REFERENCES securities(id),
    date            TEXT NOT NULL,
    open            REAL,
    high            REAL,
    low             REAL,
    close           REAL NOT NULL,
    adj_close       REAL,
    volume          INTEGER,
    source          TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (security_id, date)
) WITHOUT ROWID;

CREATE INDEX idx_prices_date ON prices(date);

-- Performance-tracking för rekommendationer
CREATE TABLE recommendation_performance (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    recommendation_id   INTEGER NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
    price_at_rec        REAL,
    price_1d            REAL,
    price_7d            REAL,
    price_30d           REAL,
    price_90d           REAL,
    price_365d          REAL,
    return_1d           REAL,
    return_7d           REAL,
    return_30d          REAL,
    return_90d          REAL,
    return_365d         REAL,
    calculated_at       TEXT,
    is_complete         INTEGER DEFAULT 0,

    UNIQUE(recommendation_id)
);
```

### 3.5 Load Tracking

```sql
-- Spåra laddade filer för idempotens
CREATE TABLE load_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path       TEXT NOT NULL,
    file_hash       TEXT NOT NULL,
    file_type       TEXT,                  -- 'podcast', 'twitter'
    loaded_at       TEXT DEFAULT CURRENT_TIMESTAMP,
    analysis_id     INTEGER REFERENCES analyses(id),
    status          TEXT DEFAULT 'success', -- 'success', 'failed', 'skipped'
    error_message   TEXT,

    UNIQUE(file_path, file_hash)
);
```

---

## 4. Loader-arkitektur

### 4.1 Klassstruktur

```python
class BaseLoader:
    """Gemensam logik för alla loaders."""

    def resolve_security(self, session, name, ticker=None) -> Security | None
    def create_recommendation(self, session, analysis_id, data) -> Recommendation
    def compute_content_hash(self, data: dict) -> str
    def should_load(self, session, file_path, file_hash) -> bool

class PodcastLoader(BaseLoader):
    """Laddar podcast-analyser från JSON."""

    def load(self, json_path: Path, session: Session) -> LoadResult
    def parse_episode(self, data: dict) -> EpisodeData
    def validate(self, data: dict) -> None  # Pydantic

class TwitterLoader(BaseLoader):
    """Laddar Twitter-analyser från JSON."""

    def load(self, json_path: Path, session: Session) -> LoadResult
    def group_by_date(self, recommendations: list) -> dict[str, list]
```

### 4.2 Idempotens via content hash

```python
def load_with_versioning(self, json_path, session):
    data = json.load(json_path)
    content_hash = self.compute_content_hash(data)

    # Kolla om exakt denna version redan finns
    existing = session.query(Analysis).filter_by(
        content_id=content_id,
        content_hash=content_hash
    ).first()

    if existing:
        return LoadResult(status='skipped', reason='unchanged')

    # Skapa ny version
    latest_version = get_latest_version(session, content_id)
    analysis = Analysis(
        content_id=content_id,
        version=latest_version + 1,
        content_hash=content_hash,
        ...
    )
```

---

## 5. CLI-kommandon

```bash
# Initiera databas
podstock db init

# Ladda all data
podstock db load

# Ladda specifik källa
podstock db load --source fillorkill
podstock db load --type twitter

# Status
podstock db status

# Sök
podstock db search "Betsson"
podstock db search --ticker EVO.ST
podstock db search --action buy --since 2025-01-01

# Pending securities
podstock db pending list
podstock db pending resolve 42 --security-id 15
podstock db pending reject 42

# Seed securities från ticker_mapping.json
podstock db seed-securities
```

---

## 6. Seed-strategi

### Automatisk seed från befintlig data

```python
def seed_from_ticker_mapping(session, mapping_path: Path):
    """Seeda securities från data/prices/ticker_mapping.json"""

    data = json.load(mapping_path)

    for name, ticker in data['mappings'].items():
        # Bestäm exchange och market från ticker-suffix
        exchange, market = parse_ticker_suffix(ticker)

        security = get_or_create_security(
            session,
            ticker=ticker,
            name=name,
            exchange=exchange,
            market=market
        )

        # Lägg till alias om det skiljer sig från name
        if name.lower() != security.name.lower():
            add_alias(session, security.id, name)

    # Lägg till aliases från 'aliases'-sektionen
    for alias, canonical in data['aliases'].items():
        security = get_security_by_name(session, canonical)
        if security:
            add_alias(session, security.id, alias)
```

### Ticker-suffix parsing

```python
def parse_ticker_suffix(ticker: str) -> tuple[str, str]:
    """'EVO.ST' -> ('OMX', 'sweden')"""

    SUFFIX_MAP = {
        '.ST': ('OMX', 'sweden'),
        '.CO': ('OMX', 'denmark'),
        '.HE': ('OMX', 'finland'),
        '.L': ('LSE', 'europe'),
        '-USD': ('CRYPTO', 'crypto'),
    }

    for suffix, (exchange, market) in SUFFIX_MAP.items():
        if ticker.endswith(suffix):
            return exchange, market

    # Default: USA
    return 'NYSE', 'usa'
```

---

## 7. Implementationsordning

### Fas 1: Grundstruktur (dag 1)
- [ ] Skapa `src/podstock/db/` med alla filer
- [ ] Implementera schema.sql
- [ ] Implementera engine.py (connection, init_db)
- [ ] Implementera models.py (SQLAlchemy ORM)
- [ ] CLI: `podstock db init`

### Fas 2: Seed & Securities (dag 1)
- [ ] Implementera ticker_lookup.py
- [ ] seed_from_ticker_mapping()
- [ ] CLI: `podstock db seed-securities`
- [ ] Verifiera med ~150 aktier

### Fas 3: Podcast Loader (dag 2)
- [ ] Implementera BaseLoader
- [ ] Implementera PodcastLoader med Pydantic-validering
- [ ] Content hash för versionering
- [ ] CLI: `podstock db load --source fillorkill`
- [ ] Testa med 400 Fill or Kill-avsnitt

### Fas 4: Twitter Loader (dag 2)
- [ ] Implementera TwitterLoader
- [ ] Hantera datum-gruppering
- [ ] CLI: `podstock db load --type twitter`

### Fas 5: Queries & Search (dag 3)
- [ ] Implementera queries.py
- [ ] CLI: `podstock db search`
- [ ] CLI: `podstock db status`

### Fas 6: Pending & Prisintegration (dag 3)
- [ ] pending_securities workflow
- [ ] Integrera med befintlig prismodul
- [ ] recommendation_performance

---

## 8. .gitignore tillägg

```gitignore
# Database
data/podstock.db
data/podstock.db-journal
data/podstock.db-wal
data/podstock.db-shm
```

---

## 9. Dokumentation

Efter implementation, uppdatera:
- [ ] README.md med databas-sektion
- [ ] ARCHITECTURE.md med db-modulen
- [ ] docs/database.md (denna fil → user guide)
