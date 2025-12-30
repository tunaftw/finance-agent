-- PodStock SQLite Database Schema
-- Version: 1.0
-- Regenerate with: podstock db init --force

-- Aktivera foreign keys (krävs vid varje connection)
PRAGMA foreign_keys = ON;

-- ============================================
-- CORE TABLES
-- ============================================

-- Innehållskällor (podcasts, twitter-konton, youtube-kanaler)
CREATE TABLE IF NOT EXISTS sources (
    id              TEXT PRIMARY KEY,      -- 'fillorkill', 'vildkatten'
    type            TEXT NOT NULL,         -- 'podcast', 'twitter', 'youtube'
    name            TEXT NOT NULL,         -- 'Fill or Kill'
    description     TEXT,
    language        TEXT DEFAULT 'sv',
    extra_data      TEXT,                  -- JSON metadata
    active          INTEGER DEFAULT 1,
    trust_rating    INTEGER DEFAULT 0,     -- -1 to 3 scale: -1=unreliable, 0=neutral, 1=positive, 2=very positive, 3=GOAT
    trust_notes     TEXT,                  -- Free text explaining trust rating
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Allt innehåll (episodes, tweets, videos)
CREATE TABLE IF NOT EXISTS content (
    id              TEXT PRIMARY KEY,      -- 'fillorkill-2025-12-23-cf58'
    source_id       TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    type            TEXT NOT NULL,         -- 'episode', 'tweet', 'video'
    external_id     TEXT,                  -- tweet_id, video_id, guid
    title           TEXT,
    published_at    TEXT NOT NULL,
    raw_text        TEXT,
    word_count      INTEGER,
    duration_seconds INTEGER,
    extra_data      TEXT,                  -- JSON metadata
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_content_source ON content(source_id);
CREATE INDEX IF NOT EXISTS idx_content_published ON content(published_at);
CREATE INDEX IF NOT EXISTS idx_content_type ON content(type);

-- Versionerade analyser
CREATE TABLE IF NOT EXISTS analyses (
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

CREATE INDEX IF NOT EXISTS idx_analyses_content ON analyses(content_id);
CREATE INDEX IF NOT EXISTS idx_analyses_hash ON analyses(content_hash);

-- View för senaste version
DROP VIEW IF EXISTS current_analyses;
CREATE VIEW current_analyses AS
SELECT * FROM analyses a1
WHERE version = (
    SELECT MAX(version) FROM analyses a2
    WHERE a2.content_id = a1.content_id
);

-- ============================================
-- SECURITIES & TICKER LOOKUP
-- ============================================

-- Värdepapper/aktier
CREATE TABLE IF NOT EXISTS securities (
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

CREATE INDEX IF NOT EXISTS idx_securities_ticker ON securities(ticker);
CREATE INDEX IF NOT EXISTS idx_securities_name ON securities(name);

-- Alternativa namn för lookup
CREATE TABLE IF NOT EXISTS security_aliases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    security_id     INTEGER NOT NULL REFERENCES securities(id) ON DELETE CASCADE,
    alias           TEXT NOT NULL,
    alias_type      TEXT DEFAULT 'name',   -- 'name', 'ticker_variant', 'twitter'

    UNIQUE(alias)
);

CREATE INDEX IF NOT EXISTS idx_aliases_alias ON security_aliases(alias);

-- Relationer mellan samma bolag på olika börser
CREATE TABLE IF NOT EXISTS security_relations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    primary_id      INTEGER NOT NULL REFERENCES securities(id),
    related_id      INTEGER NOT NULL REFERENCES securities(id),
    relation_type   TEXT,                  -- 'same_company', 'adr', 'dual_listing'

    UNIQUE(primary_id, related_id)
);

-- Omatchade aktier för manuell granskning
CREATE TABLE IF NOT EXISTS pending_securities (
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

-- ============================================
-- RECOMMENDATIONS & MENTIONS
-- ============================================

-- Rekommendationer (tydliga köp/sälj-signaler)
CREATE TABLE IF NOT EXISTS recommendations (
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

CREATE INDEX IF NOT EXISTS idx_rec_analysis ON recommendations(analysis_id);
CREATE INDEX IF NOT EXISTS idx_rec_security ON recommendations(security_id);
CREATE INDEX IF NOT EXISTS idx_rec_action ON recommendations(action);
CREATE INDEX IF NOT EXISTS idx_rec_unmatched ON recommendations(raw_stock_name)
    WHERE security_id IS NULL;

-- Omnämnanden (utan tydlig signal)
CREATE TABLE IF NOT EXISTS mentions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id     INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    security_id     INTEGER REFERENCES securities(id) ON DELETE SET NULL,
    raw_stock_name  TEXT NOT NULL,
    raw_ticker      TEXT,
    sentiment       TEXT,                  -- 'positive', 'negative', 'neutral'
    context         TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mentions_analysis ON mentions(analysis_id);
CREATE INDEX IF NOT EXISTS idx_mentions_security ON mentions(security_id);

-- Key takeaways
CREATE TABLE IF NOT EXISTS key_takeaways (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id     INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    takeaway        TEXT NOT NULL,
    sort_order      INTEGER DEFAULT 0
);

-- ============================================
-- PRICES & PERFORMANCE
-- ============================================

-- Historisk prisdata
CREATE TABLE IF NOT EXISTS prices (
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

CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date);

-- Performance-tracking för rekommendationer
CREATE TABLE IF NOT EXISTS recommendation_performance (
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

    -- Current price tracking (updated on each sync)
    price_current       REAL,           -- Latest fetched price
    price_current_date  TEXT,           -- YYYY-MM-DD when current price was fetched
    ticker_used         TEXT,           -- Yahoo Finance ticker used for lookup
    return_current      REAL,           -- Return from rec to current price

    UNIQUE(recommendation_id)
);

-- ============================================
-- LOAD TRACKING
-- ============================================

-- Spåra laddade filer för idempotens
CREATE TABLE IF NOT EXISTS load_log (
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


-- ============================================
-- UNIFIED SIGNAL LAYER
-- ============================================

-- Speaker identities för cross-source linking
CREATE TABLE IF NOT EXISTS speaker_identities (
    id              TEXT PRIMARY KEY,      -- 'anders-stogh'
    display_name    TEXT NOT NULL,         -- 'Anders Stogh'
    aliases         TEXT,                  -- JSON array
    podcast_names   TEXT,                  -- JSON array
    twitter_handles TEXT,                  -- JSON array
    youtube_channels TEXT,                 -- JSON array
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Unified signals från alla källor
CREATE TABLE IF NOT EXISTS unified_signals (
    id              TEXT PRIMARY KEY,      -- SHA256 hash
    source_type     TEXT NOT NULL,         -- 'podcast', 'youtube', 'twitter'
    source_id       TEXT NOT NULL,         -- 'kortochlang', 'technicalroundup'
    content_id      TEXT NOT NULL,         -- Episode/video/tweet ID
    content_date    TEXT NOT NULL,         -- ISO date

    -- Asset
    asset_symbol    TEXT NOT NULL,         -- 'BTC', 'VOLVO_B'
    asset_name      TEXT NOT NULL,         -- 'Bitcoin', 'Volvo'
    asset_type      TEXT NOT NULL,         -- 'crypto', 'stock'

    -- Signal
    signal          TEXT NOT NULL,         -- 'bullish', 'bearish', 'neutral'
    signal_strength TEXT NOT NULL,         -- 'strong', 'moderate', 'weak'
    original_action TEXT,                  -- Original value before normalization

    -- Speaker
    speaker_name    TEXT NOT NULL,
    speaker_id      TEXT REFERENCES speaker_identities(id),

    -- Context
    quote           TEXT,
    reasoning       TEXT,
    timestamp       TEXT,                  -- Position in content
    price_levels    TEXT,                  -- JSON array

    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_unified_signals_content_date ON unified_signals(content_date);
CREATE INDEX IF NOT EXISTS ix_unified_signals_asset_symbol ON unified_signals(asset_symbol);
CREATE INDEX IF NOT EXISTS ix_unified_signals_speaker_name ON unified_signals(speaker_name);
CREATE INDEX IF NOT EXISTS ix_unified_signals_signal ON unified_signals(signal);
CREATE INDEX IF NOT EXISTS ix_unified_signals_source_type ON unified_signals(source_type);
