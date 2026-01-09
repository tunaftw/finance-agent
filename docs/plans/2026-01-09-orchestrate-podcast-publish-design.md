# Design: orchestrate-podcast-publish

**Datum:** 2026-01-09
**Status:** Godkänd

## Syfte

En master orchestration skill som kör hela pipelinen från nya podcast-avsnitt till publicerad hemsida.

## Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATE-PODCAST-PUBLISH                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. PRE-FLIGHT  ──→  Validera miljö                            │
│                         │                                       │
│                         ▼                                       │
│  2. DOWNLOAD    ──→  podcast-download skill                     │
│     (Apple Podcasts / Whisper)                                  │
│                         │                                       │
│                         ▼                                       │
│  3. ANALYZE     ──→  analyze skill (OpenCode/GLM-4.7)          │
│     (batch mode)                                                │
│                         │                                       │
│                         ▼                                       │
│  4. SYNC DB     ──→  database-analyze-sync skill               │
│                  ──→  price-sync skill (lokalt)                 │
│                         │                                       │
│                         ▼                                       │
│  5. PUBLISH     ──→  dashboard generate --no-embed             │
│                  ──→  git commit & push                         │
│                  ──→  Vercel auto-deploy                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Beslut

| Aspekt | Beslut |
|--------|--------|
| **Namn** | `/orchestrate-podcast-publish` |
| **Analysmetod** | OpenCode/GLM-4.7 (batch) |
| **Transkribering** | Apple Podcasts först, Whisper som fallback |
| **Felhantering** | Retry 2-3x → skip & fortsätt (utom Dashboard/Git = stopp) |
| **Självförbättring** | Fixa autonomt, rapportera i slutet |
| **Feedback** | Smart: tyst vid OK, detaljerad vid problem |
| **Git** | Allt i en commit per körning |
| **Loggar** | `logs/orchestration/latest.md` + timestampade arkiv |
| **Konfiguration** | Hårdkodad i SKILL.md |
| **Trigger** | Manuellt, dagligen, eller veckovis |

## Detaljerat Workflow

### Steg 1: Pre-flight Check

Innan något körs, validera att miljön är redo:

```
PRE-FLIGHT CHECKLIST
────────────────────
✓ Apple Podcasts DB finns och är tillgänglig
✓ data/podcast_mapping.json finns
✓ data/podstock.db finns (eller init:as)
✓ OpenCode/GLM-4.7 är körbart (scripts/batch_runner.py)
✓ Git working tree är ren (inga uncommitted changes)
```

Om något saknas → stoppa med tydligt felmeddelande.

### Steg 2: Download (podcast-download)

```python
# Kör check_sync_status.py för att hitta osynkade avsnitt
# Filtrera på 2025+ (hårdkodat)

for episode in unsynced_episodes:
    try:
        # Försök 1: Apple Podcasts transcript
        transcript = fetch_apple_transcript(episode)
    except NotFound:
        try:
            # Försök 2: Whisper transkribering
            transcript = whisper_transcribe(episode)
        except Error as e:
            # Retry 2x, sedan skip
            log_failure(episode, e)
            continue

    save_transcript(episode, transcript)
```

**Output:** Nya `.txt`-filer i `data/transcripts/{podcast}/`

### Steg 3: Analyze (analyze skill)

```python
# Generera kö-fil med oanalyserade transkript
# Kör OpenCode/GLM-4.7 batch i separat process

queue_file = generate_transcript_queue()
# → data/podcasts/analyses-v2/transcript-queue.txt

# Starta batch runner och vänta på completion
run_batch_analysis(queue_file, model="glm-4.7")

# Övervaka progress via completion-log.json
wait_for_completion(timeout=30min)
```

**Output:** Nya `.json`-filer i `data/podcasts/analyses-v2/`

### Steg 4: Database Sync

```python
# Synka nya analyser till SQLite
sync_analyses_to_db()
# → Laddar JSON → recommendations, mentions, insights tabeller

# Synka priser (endast lokalt bibliotek, inga API-anrop)
sync_prices_local_only()
# → Matchar recommendations mot prices-tabellen
# → Beräknar return_current för befintliga priser

# Om nya tickers saknar prishistorik:
if missing_tickers:
    log_info(f"OBS: {len(missing_tickers)} tickers saknar pris")
```

**Output:** Uppdaterad `data/podstock.db`

### Steg 5: Dashboard & Publish

```python
# Regenerera dashboard JSON-filer
run("podstock dashboard generate --no-embed")
# → data/analyses.json, data/podcasts.json, data/recommendations.json

# Git commit allt i en commit
files_to_commit = [
    "data/transcripts/",
    "data/podcasts/analyses-v2/",
    "data/podstock.db",
    "data/*.json",
    "index.html",
    ".claude/skills/",
]

commit_message = f"""feat(data): sync {n_episodes} podcast episodes

- Downloaded: {n_downloaded} transcripts
- Analyzed: {n_analyzed} episodes
- Recommendations: {n_recs} new
- Skills updated: {updated_skills or 'none'}

🤖 Generated with orchestrate-podcast-publish
"""

git_add_commit_push(files_to_commit, commit_message)
```

**Output:** Push till main → Vercel auto-deploy → Hemsida uppdaterad

## Felhantering

| Steg | Retry | Fallback | Vid fortsatt fel |
|------|-------|----------|------------------|
| Download | 2x | Apple → Whisper | Skip episode |
| Analyze | 3x | - | Skip transcript |
| DB Sync | 2x | - | Skip fil |
| Price Sync | - | Endast lokalt | Logga saknade |
| Dashboard | 2x | - | **STOPP** (kritiskt) |
| Git Push | 3x | - | **STOPP** (kritiskt) |

## Självförbättring

Under körningen övervakar orchestration-skillen för:

1. **Sökvägsfel** → Fixar paths i skill-filer automatiskt
2. **Saknade mappings** → Lägger till i podcast_mapping.json
3. **Script-fel** → Uppdaterar script-anrop om syntax ändrats
4. **Timeout-värden** → Justerar om något konsekvent tar för lång tid
5. **Deprecated kod** → Ersätter gamla funktionsanrop

Alla förbättringar rapporteras i slutrapporten.

## Loggning

```
logs/
└── orchestration/
    ├── latest.md                    # Senaste körningen
    ├── 2026-01-09T20-30-00.md      # Arkiverade körningar
    └── ...
```

### Slutrapport-mall

```
════════════════════════════════════════════════════════════════════
ORCHESTRATE-PODCAST-PUBLISH COMPLETE
════════════════════════════════════════════════════════════════════

RESULTAT
────────
✓ Downloaded:  X transcripts (Y Apple, Z Whisper)
✓ Analyzed:    X episodes → Y recommendations
✓ DB synced:   X analyses, Y recs, Z insights
✓ Prices:      X/Y recs matched (Z saknar prishistorik)
✓ Published:   Commit {hash} pushed → Vercel deploying

SJÄLVFÖRBÄTTRINGAR
──────────────────
• {skill}: {beskrivning av fix}

SKIPPADE (kräver manuell åtgärd)
────────────────────────────────
• {episode}: {anledning}

TIMING
──────
Total tid:     Xm Ys
  Download:    Xm Ys
  Analyze:     Xm Ys
  Sync:        Xm Ys
  Publish:     Xm Ys

════════════════════════════════════════════════════════════════════
```

## Smart Feedback

- **Normal körning (allt OK):** Minimal output, bara steg-markörer
- **Vid problem:** Detaljerad output med retry-info och felmeddelanden

## Filstruktur

```
.claude/skills/orchestrate-podcast-publish/
├── SKILL.md                    # Huvudskill med workflow
└── references/
    ├── pre-flight.md           # Pre-flight check detaljer
    ├── improvement-rules.md    # Regler för automatiska fixar
    └── report-template.md      # Mall för slutrapport
```

## Beroenden

Skills som anropas:

1. `podcast-download` - hämta transkript
2. `analyze` - analysera med GLM-4.7
3. `database-analyze-sync` - synka analyser till DB
4. `price-sync` - synka priser (endast lokalt)

## Hårdkodade Värden

```
year_filter:        2025      # Filtrera podcasts från detta år
retry_attempts:     3         # Max retry-försök
whisper_timeout:    15 min    # Timeout för Whisper
analysis_model:     glm-4.7   # Modell för batch-analys
log_retention:      30 dagar  # Behåll loggar
```

## Nästa Steg

1. Skapa skill-filen `.claude/skills/orchestrate-podcast-publish/SKILL.md`
2. Skapa `logs/orchestration/` mapp
3. Testa körning med ett fåtal podcasts
4. Verifiera att hemsidan uppdateras korrekt
