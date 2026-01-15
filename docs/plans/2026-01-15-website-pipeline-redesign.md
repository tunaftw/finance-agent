# Website Pipeline Redesign

**Version:** 1.1
**Datum:** 2026-01-15
**Status:** Approved - Implementation Started

---

## Executive Summary

Denna design adresserar tre sammankopplade problem som hindrar nya podcast-analyser från att visas på hemsidan:

1. **Database sync gap** - Nya JSON-analyser synkas inte till databasen innan dashboard genereras
2. **Git 100 MB-gräns** - `index.html` är 102.6 MB (embedded mode) vilket blockerar push
3. **Multi-device sync** - Risk att tappa data när man byter mellan enheter

**Lösningen implementeras i två faser:**
- **Fas 1:** Fixar akuta problemet genom att optimera Git-workflow och pipeline
- **Fas 2:** Migrerar till cloud-databas för robust multi-device sync

---

## Problem Analysis

### Rotorsak: Trasigt Dataflöde

```
JSON-analyser ──────┐
                    │
                    ▼
              ┌──────────┐       ┌───────────┐       ┌──────────┐
              │ DB Sync  │──?──► │ Dashboard │──?──► │ Git Push │
              │ (MISSAS) │       │ Generator │       │ (102MB!) │
              └──────────┘       └───────────┘       └──────────┘
```

**Symptom:**
- Veckans Trade avsnitt från Jan 14 analyserat men hemsidan visar Jan 7
- Git varnar för filer över 100 MB
- 103 podcast-analyser finns som JSON men saknas i databasen

**Filstorlekar (nuvarande):**

| Fil | Storlek | GitHub Gräns | Status |
|-----|---------|--------------|--------|
| `index.html` | 102.6 MB | 100 MB | BLOCKERAD |
| `data/podcasts.json` | 76 MB | 100 MB | Närmar sig gränsen |
| `data/recommendations.json` | 31 MB | 100 MB | OK för nu |

---

## Fas 1: Git-optimerad Pipeline (FÖRENKLAD)

> **Uppdatering 2026-01-15:** Efter analys valdes en förenklad approach där aggregerade
> filer behålls i Git men `--no-embed` mode används för att hålla index.html liten.
> Detta undviker komplexiteten med Vercel Python-builds och löser det akuta problemet.

### Mål
- Fixa 100 MB-problemet omedelbart
- Säkerställ att nya analyser alltid når hemsidan
- Behåll multi-device sync via Git

### 1.1 Arkitektur (Förenklad)

**Princip:** Allt data i Git, men `index.html` genereras ALLTID med `--no-embed`.

```
┌─────────────────────────────────────────────────────────────────┐
│                    FÖRENKLAD PIPELINE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Analysera podcasts → JSON-filer                              │
│  2. Synka till databas (KRITISK!)                                │
│  3. Generera dashboard med --no-embed                            │
│  4. Git commit (index.html ~150KB, data/*.json ~120MB totalt)    │
│  5. Git push → Vercel serverar statiska filer                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Filstruktur

**Vad som trackas i Git:**
```
data/
├── podcasts.json          (76 MB) ← TRACKAD - under 100MB gräns
├── recommendations.json   (31 MB) ← TRACKAD - under 100MB gräns
├── analyses.json          (5 MB)  ← TRACKAD
├── twitter.json           (5 MB)  ← TRACKAD
├── youtube.json           (3 MB)  ← TRACKAD
└── podcasts/
    └── analyses-v2/       (50 MB) ← TRACKAD (source of truth)

assets/                    ← TRACKAD (JS/CSS)
```

**Vad som INTE trackas:**
```
index.html                 ← GITIGNORED (kan vara 100MB+ med embed)
data/podstock.db           ← GITIGNORED (regenereras lokalt)
data/dashboard/            ← GITIGNORED (build output)
```

### 1.3 Uppdaterad .gitignore (Förenklad)

```gitignore
# Root index.html - MÅSTE genereras med --no-embed för att undvika 100MB+
index.html

# Databas (regenereras lokalt)
data/podstock.db
data/analyses.db
data/database.db

# Dashboard build output
data/dashboard/
```

**OBS:** Aggregerade JSON-filer (podcasts.json, recommendations.json etc.) BEHÅLLS i Git
eftersom de är under 100MB-gränsen. Detta förenklar deployment avsevärt.

### 1.4 Deploy Process (Förenklad)

Ingen Vercel-build krävs. Vercel serverar statiska filer direkt från Git.

**Lokal build-process (körs innan git push):**

```bash
#!/bin/bash
set -e

echo "=== VERCEL BUILD ==="

# 1. Install dependencies
pip install -e .

# 2. Initialize database
python -m podstock db init

# 3. Load all analyses from JSON files
python -m podstock db load --type podcast
python -m podstock db load --type twitter
python -m podstock db load --type youtube

# 4. Generate dashboard (no-embed mode)
python -m podstock dashboard generate --no-embed --output dist/

# 5. Verify output
if [ ! -f "dist/index.html" ]; then
    echo "ERROR: index.html not generated"
    exit 1
fi

EPISODE_COUNT=$(python3 -c "import json; d=json.load(open('dist/data/podcasts.json')); print(len(d.get('episodes', [])))")
echo "Generated dashboard with $EPISODE_COUNT episodes"

if [ "$EPISODE_COUNT" -lt 100 ]; then
    echo "WARNING: Low episode count - verify data integrity"
fi

echo "=== BUILD COMPLETE ==="
```

### 1.5 Verification Gates

Varje steg i pipelinen får en gate som måste passeras:

**Gate 1: Pre-sync**
```python
def verify_pre_sync():
    """Verifiera att det finns nya analyser att synka."""
    json_count = len(list(Path('data/podcasts/analyses-v2').glob('*-20??-??-??-????.json')))
    return {"json_files": json_count, "status": "proceed" if json_count > 0 else "skip"}
```

**Gate 2: Post-sync (KRITISK)**
```python
def verify_post_sync(expected_new: int):
    """Verifiera att DB sync lyckades."""
    recent = query("""
        SELECT COUNT(*) FROM load_log
        WHERE status='success' AND loaded_at > datetime('now', '-5 minutes')
    """)

    if recent < expected_new * 0.9:
        return {"status": "fail", "action": "STOPP - DB sync misslyckades"}
    return {"status": "pass", "synced": recent}
```

**Gate 3: Export size check**
```python
def verify_export_sizes():
    """Verifiera att inga filer överskrider Git-gränsen."""
    MAX_SIZES = {
        'index.html': 500_000,  # 500 KB (no-embed mode)
        'data/podcasts.json': 90_000_000,  # 90 MB varning
    }

    for file, max_size in MAX_SIZES.items():
        if Path(file).exists() and Path(file).stat().st_size > max_size:
            return {"status": "fail", "file": file, "action": "Kontrollera --no-embed"}
    return {"status": "pass"}
```

**Gate 4: Pre-push sanity check**
```python
def verify_pre_push():
    """Verifiera att senaste analysen finns i export."""
    latest_analysis = max(
        Path('data/podcasts/analyses-v2').glob('*.json'),
        key=lambda p: p.stat().st_mtime
    )

    with open('data/podcasts.json') as f:
        episodes = json.load(f).get('episodes', [])

    episode_ids = [e['episode_id'] for e in episodes]

    if latest_analysis.stem not in episode_ids:
        return {"status": "fail", "missing": latest_analysis.stem}
    return {"status": "pass", "latest": latest_analysis.stem}
```

### 1.6 Uppdaterad Orchestration Skill

**Ny pipeline ordning:**

```
1. PRE-FLIGHT CHECK
   ├── Validera miljö
   ├── Kolla Git working tree
   └── Gate: Alla förutsättningar OK?

2. DOWNLOAD TRANSCRIPTS
   ├── Kolla sync status
   ├── Visa preview, fråga användaren
   ├── Ladda ner via Apple/Whisper
   └── Gate: Transkript sparade?

3. ANALYZE
   ├── Hitta oanalyserade transkript
   ├── Kör Claude Code eller OpenCode
   ├── Validera JSON-schema
   └── Gate: Alla analyser har korrekt format?

4. DATABASE SYNC (KRITISK)
   ├── Räkna nya filer
   ├── Kör: podstock db load --type podcast
   ├── Verifiera load_log
   └── Gate: Synkade filer == förväntade?

5. GIT COMMIT & PUSH
   ├── git add data/podcasts/analyses-v2/*.json
   ├── git add data/transcripts/
   ├── Verifiera inga stora filer i staging
   ├── git commit
   └── git push

6. VERIFY DEPLOY
   ├── Vänta på Vercel (max 3 min)
   ├── Hämta live metadata.json
   ├── Jämför latest_episode_date
   └── Gate: Senaste analysen live?
```

### 1.7 Lokal Utveckling

För att jobba lokalt behöver man generera aggregatfiler manuellt:

```bash
# Setup på ny enhet
git clone <repo>
cd podstock
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Generera lokal databas och dashboard
python -m podstock db init
python -m podstock db load --type podcast
python -m podstock dashboard generate --no-embed

# Öppna lokalt
open data/dashboard/index.html
```

**Dagligt arbete:**
```bash
# Analysera nya podcasts...
# JSON-filer skapas i data/podcasts/analyses-v2/

# Committa endast analysfiler
git add data/podcasts/analyses-v2/
git add data/transcripts/
git commit -m "feat(data): add new analyses"
git push

# Vercel bygger automatiskt och genererar aggregatfiler
```

---

## Fas 2: Cloud-databas Migration

### Mål
- Noll lokalt lagrat (bara kod i Git)
- Realtidssynk mellan alla enheter
- Hemsidan läser direkt från cloud DB

### 2.1 Arkitektur

```
┌─────────────┐                              ┌─────────────┐
│   Laptop    │────── write ────────────────►│             │
└─────────────┘                              │             │
                                             │   Turso     │
┌─────────────┐                              │   Cloud DB  │
│  Mac Mini   │────── write ────────────────►│             │
└─────────────┘                              │             │
                                             │  (9 GB      │
┌─────────────┐                              │   gratis)   │
│   Vercel    │◄───── read ─────────────────│             │
│  (hemsida)  │                              └─────────────┘
└─────────────┘

┌─────────────┐
│   GitHub    │  ← Endast KOD, inga data-filer
└─────────────┘
```

### 2.2 Varför Turso?

| Tjänst | Typ | Gratis Tier | Fördel |
|--------|-----|-------------|--------|
| **Turso** | SQLite (edge) | 9 GB, 500M reads/mån | Samma SQL som nu |
| Supabase | PostgreSQL | 500 MB | Kräver SQL-ändringar |
| PlanetScale | MySQL | 5 GB | Kräver SQL-ändringar |

**Turso valdes för:**
- Kompatibelt med befintlig SQLite-kod
- Generös gratis tier (9 GB)
- Edge-optimerad (snabb globalt)
- Stöd för lokal sync-kopia (offline-arbete)

### 2.3 Kodändringar

**src/podstock/db/engine.py:**

```python
import os
from sqlalchemy import create_engine

def get_engine():
    """Get database engine - cloud or local."""
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")

    if turso_url and turso_token:
        # Cloud mode (Turso)
        # Using libsql dialect for Turso
        connection_string = f"sqlite+libsql://{turso_url}?authToken={turso_token}"
        return create_engine(connection_string)
    else:
        # Local mode (fallback)
        return create_engine("sqlite:///data/podstock.db")
```

**Alternativ med embedded replicas (offline-stöd):**

```python
import libsql_experimental as libsql
import os

def get_connection():
    """Get database connection with sync support."""
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")

    if turso_url:
        # Synkad lokal kopia + cloud
        conn = libsql.connect(
            "data/local-replica.db",
            sync_url=turso_url,
            auth_token=turso_token
        )
        conn.sync()  # Synka med cloud vid start
        return conn
    else:
        # Pure local
        return libsql.connect("data/podstock.db")
```

### 2.4 Dataflöde (Fas 2)

**Ny pipeline:**

```
1. Download transkript
         │
         ▼
2. Analysera med Claude/GLM
         │
         ▼
3. Spara direkt till Turso ──────────► [Cloud DB]
         │                                  │
         ▼                                  ▼
4. Verifiera på hemsidan ◄──────────── [Vercel läser]

(Inget Git-steg för data!)
```

### 2.5 Git-struktur (Fas 2)

```
podstock/
├── src/                    ← KOD (i Git)
├── scripts/                ← KOD (i Git)
├── .claude/skills/         ← KOD (i Git)
├── docs/                   ← DOCS (i Git)
├── tests/                  ← TESTER (i Git)
├── pyproject.toml          ← CONFIG (i Git)
├── data/
│   ├── local-replica.db    ← GITIGNORED (lokal sync)
│   └── podcast_mapping.json ← I Git (liten config)
└── vercel.json             ← CONFIG (i Git)
```

**Git-repo storlek: ~5 MB** (bara kod)

### 2.6 Hemsida-integration

**Option A: API Routes (Next.js/Vercel Functions)**

```javascript
// pages/api/episodes.js
import { createClient } from '@libsql/client';

export default async function handler(req, res) {
  const client = createClient({
    url: process.env.TURSO_DATABASE_URL,
    authToken: process.env.TURSO_AUTH_TOKEN,
  });

  const result = await client.execute(`
    SELECT a.*, c.title, c.date, s.name as source_name
    FROM analyses a
    JOIN content c ON a.content_id = c.id
    JOIN sources s ON c.source_id = s.id
    ORDER BY c.date DESC
    LIMIT 100
  `);

  res.json(result.rows);
}
```

**Option B: Edge Functions (snabbare)**

```javascript
// api/episodes.js
export const config = { runtime: 'edge' };

export default async function handler(req) {
  const client = createClient({
    url: process.env.TURSO_DATABASE_URL,
    authToken: process.env.TURSO_AUTH_TOKEN,
  });

  const result = await client.execute('SELECT * FROM analyses...');

  return new Response(JSON.stringify(result.rows), {
    headers: { 'Content-Type': 'application/json' }
  });
}
```

### 2.7 Migrationsplan

```
Vecka 1: Setup Turso
├── [ ] Skapa Turso-konto på turso.tech
├── [ ] Skapa databas "podstock-prod"
├── [ ] Notera DATABASE_URL och AUTH_TOKEN
├── [ ] Lägg till i .env.local
└── [ ] Testa connection: turso db shell podstock-prod

Vecka 2: Migrera data
├── [ ] Exportera lokal SQLite: sqlite3 data/podstock.db .dump > backup.sql
├── [ ] Importera till Turso: turso db shell podstock-prod < backup.sql
├── [ ] Verifiera radantal: SELECT COUNT(*) FROM analyses
├── [ ] Uppdatera engine.py med dual-mode
└── [ ] Testa lokalt med TURSO_DATABASE_URL satt

Vecka 3: Uppdatera hemsida
├── [ ] Skapa API-route eller edge function
├── [ ] Uppdatera frontend att läsa från API
├── [ ] Lägg till env vars i Vercel dashboard
├── [ ] Deploya och testa
└── [ ] Verifiera att nya analyser syns direkt

Vecka 4: Städa Git
├── [ ] Installera BFG Repo-Cleaner
├── [ ] Ta bort stora filer från historik
├── [ ] Uppdatera .gitignore
├── [ ] Force push clean repo
├── [ ] Verifiera repo-storlek < 50 MB
└── [ ] Dokumentera ny workflow
```

### 2.8 Kostnadsanalys

| Resurs | Användning | Kostnad |
|--------|------------|---------|
| Turso DB | ~200 MB data | $0 (9 GB gratis) |
| Turso reads | ~10K/dag | $0 (500M/mån gratis) |
| Turso writes | ~100/dag | $0 (inkluderat) |
| Vercel hosting | Static + Edge | $0 (hobby) |
| **Total** | | **$0/mån** |

---

## Implementation Summary

### Fas 1 Scope (Vecka 1-2)

| Uppgift | Prioritet | Komplexitet |
|---------|-----------|-------------|
| Uppdatera .gitignore | Hög | Låg |
| Ta bort aggregatfiler från Git | Hög | Låg |
| Konfigurera Vercel build | Hög | Medium |
| Uppdatera orchestration skill | Hög | Medium |
| Lägg till verification gates | Medium | Medium |
| Testa full pipeline | Hög | Låg |

### Fas 2 Scope (Vecka 3-6)

| Uppgift | Prioritet | Komplexitet |
|---------|-----------|-------------|
| Setup Turso | Hög | Låg |
| Migrera data | Hög | Låg |
| Uppdatera engine.py | Hög | Medium |
| Skapa API-routes | Hög | Medium |
| Uppdatera frontend | Medium | Medium |
| Städa Git-historik | Låg | Medium |

---

## Risker och Mitigering

| Risk | Sannolikhet | Impact | Mitigering |
|------|-------------|--------|------------|
| Vercel build timeout | Låg | Hög | Cache dependencies, optimera build |
| Turso nertid | Låg | Hög | Lokal replica som fallback |
| Data-förlust vid migration | Låg | Kritisk | Backup innan, verifiera efter |
| Fas 1 räcker inte (repo växer) | Medium | Medium | Påbörja Fas 2 tidigt |

---

## Success Criteria

### Fas 1 Complete
- [ ] `index.html` < 500 KB
- [ ] Inga filer > 90 MB i Git
- [ ] Nya analyser visas på hemsidan inom 5 min efter push
- [ ] Pipeline har verification gates som stoppar vid fel

### Fas 2 Complete
- [ ] Git repo < 10 MB (endast kod)
- [ ] Analyser synkas mellan enheter utan Git
- [ ] Hemsidan läser direkt från Turso
- [ ] Offline-stöd via lokal replica

---

## Approval

**Designen kräver godkännande innan implementation påbörjas.**

Godkänd av: _________________ Datum: _________________

---

## Appendix A: Nuvarande vs Ny Orchestration

**Nuvarande (problematisk):**
```
Download → Analyze → (DB sync kanske?) → Dashboard → Git commit/push
                          ↑
                    Inget verification
```

**Ny (robust):**
```
Download → [Gate] → Analyze → [Gate] → DB Sync → [Gate] →
Git commit → [Gate: size check] → Git push → [Gate: verify deploy]
```

## Appendix B: Environment Variables

**Fas 1:**
```bash
# Inga nya env vars krävs
```

**Fas 2:**
```bash
# Lokalt (.env.local)
TURSO_DATABASE_URL=libsql://podstock-prod-xxx.turso.io
TURSO_AUTH_TOKEN=eyJhbGc...

# Vercel Dashboard
# Settings → Environment Variables → Add
```

## Appendix C: Rollback Plan

**Om Fas 1 misslyckas:**
1. Återställ .gitignore
2. Generera aggregatfiler lokalt
3. Commit och push som tidigare

**Om Fas 2 misslyckas:**
1. Sätt `TURSO_DATABASE_URL` till tom sträng
2. Återgå till lokal SQLite
3. Använd Fas 1 workflow
