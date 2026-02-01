---
name: orchestrate-podcast-publish
description: Master orchestration skill som kor hela pipelinen fran nya podcast-avsnitt till publicerad hemsida. Anvand nar anvandaren sager "synka allt", "publicera podcasts", "kor hela pipelinen", eller vill uppdatera hemsidan med senaste analyserna.
---

# Orchestrate Podcast Publish

Kor hela pipelinen: download -> analyze -> sync DB -> publish hemsida.

## Quick Start

1. **Pre-flight check** - Validera miljo
2. **Download** - Visa preview, fraga anvandaren, hamta transkript
3. **Analyze** - Analysera med Claude Code eller OpenCode/GLM-4.7
4. **Sync DB** - Ladda analyser till databas
5. **Publish** - Generera dashboard, commit, push -> Vercel

## Hardkodade Varden

```
podstock_cmd:       .venv/bin/python -m podstock
year_filter:        CURRENT_YEAR  # Dynamiskt - anvand datetime.now().year
retry_attempts:     3             # Max retry-forsok
whisper_timeout:    15 min        # Timeout for Whisper
analysis_timeout:   180 sec       # Timeout per transkript-analys
```

**VIKTIGT:**
- `year_filter` bor aldrig vara hardkodat till ett specifikt ar
- Anvand alltid `.venv/bin/python -m podstock` istallet for bara `podstock`

---

## Steg 1: Pre-flight Check

**KOR ALLTID FORST.** Se [references/pre-flight.md](references/pre-flight.md) for detaljer.

```bash
# Kolla alla forutsattningar
echo "Pre-flight check..."

# 1. Apple Podcasts DB
APPLE_DB="$HOME/Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Documents/MTLibrary.sqlite"
[ -f "$APPLE_DB" ] && echo "✓ Apple Podcasts DB" || echo "✗ Apple Podcasts DB saknas"

# 2. Podcast mapping
[ -f "data/podcast_mapping.json" ] && echo "✓ Podcast mapping" || echo "✗ podcast_mapping.json saknas"

# 3. Database
[ -f "data/podstock.db" ] && echo "✓ Database" || echo "✗ podstock.db saknas"

# 4. GetBearerToken binary (for Apple transcripts)
[ -f "tools/apple-transcripts/GetBearerToken" ] && echo "✓ GetBearerToken" || echo "⚠ GetBearerToken saknas"

# 5. Bearer token status
if [ -f "tools/apple-transcripts/bearer_token.txt" ]; then
    # Check expiration
    token=$(cat tools/apple-transcripts/bearer_token.txt)
    exp=$(echo "$token" | cut -d'.' -f2 | base64 -D 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('exp',0))" 2>/dev/null)
    now=$(date +%s)
    if [ "$exp" -gt "$now" ] 2>/dev/null; then
        exp_date=$(python3 -c "from datetime import datetime; print(datetime.fromtimestamp($exp).strftime('%Y-%m-%d'))")
        echo "✓ Bearer token (expires: $exp_date)"
    else
        echo "⚠ Bearer token EXPIRED - run ./scripts/refresh_apple_token.sh"
    fi
else
    echo "⚠ Bearer token saknas - run ./scripts/refresh_apple_token.sh"
fi

# 6. Git status
git diff --quiet && echo "✓ Git working tree ren" || echo "⚠ Git har uncommitted changes"

# 7. Kolla analysmetod (OpenCode eller Claude)
[ -f "$HOME/.opencode/bin/opencode" ] && echo "✓ OpenCode tillganglig" || echo "⚠ OpenCode saknas - anvander Claude Code"
```

**Om nagot kritiskt saknas:** STOPP och meddela anvandaren.

**Om git har uncommitted changes:** Fraga anvandaren om de vill fortsatta anda eller committa forst.

---

## Steg 2: Download Transcripts

### 2a. Kolla sync-status

```bash
python3 scripts/podcast/check_sync_status.py --year $(date +%Y) --json
```

### 2b. Visa preview och fraga anvandaren

**VIKTIGT:** Innan nedladdning, visa en oversikt och fraga anvandaren.

Bygg en tabell med osynkade avsnitt:

```python
import subprocess
import json
from datetime import datetime

# Kolla sync status
result = subprocess.run(
    ["python3", "scripts/podcast/check_sync_status.py", "--year", str(datetime.now().year), "--json"],
    capture_output=True, text=True
)
status = json.loads(result.stdout)
missing = status.get("missing_episodes", [])

if not missing:
    print("✓ Alla podcasts ar synkade - hoppar till analys")
else:
    # Bygg preview-tabell
    print(f"Hittade {len(missing)} osynkade avsnitt:")
    print()
    print("| Podcast | Avsnitt | Datum | Metod |")
    print("|---------|---------|-------|-------|")
    for ep in missing[:10]:  # Visa max 10
        method = "Apple ✓" if ep.get("has_apple_transcript") else "Whisper ⚠"
        print(f"| {ep['podcast']} | {ep['title'][:30]}... | {ep['date']} | {method} |")
    if len(missing) > 10:
        print(f"| ... | +{len(missing)-10} till | ... | ... |")
```

### 2c. Valj Analysmodell

**EFTER tabellen visats, fraga anvandaren vilken modell som ska anvandas for analys:**

Anvand AskUserQuestion:
```
Fraga: "Vilken modell vill du anvanda for analys?"

Options:
1. "Claude (rekommenderas for kvalitet)"
2. "GLM-4.7 (snabbare, gratis)"
```

Spara valet for anvandning i Steg 3. Notera: Bada modeller anvander nu samma enhetliga prompt fran `prompt_templates.py`.

### 2d. Fraga om nedladdning

**Anvand AskUserQuestion:**

```
Fraga: "{X} avsnitt saknar transkript. Vad vill du gora?"

Options:
1. "Ladda ner alla {X}" - Kör hela listan
2. "Valj specifika podcasts" - Visa multiselect med podcast-namn
3. "Hoppa over nedladdning" - Ga direkt till analys
```

Om anvandaren valjer "Valj specifika", anvand multiSelect=true med podcast-namn.

### 2e. Ladda ner valda transkript

**METOD 1: Apple Podcasts (rekommenderat)**

Använd `fetch_transcript_pure_python.py` som automatiskt:
- Laddar bearer token (refreshar om expired)
- Laddar ner TTML från Apple API
- Extraherar text och sparar som transcript

```bash
# Ladda ner alla saknade för 2026
python3 scripts/fetch_transcript_pure_python.py --year 2026

# Begränsa antal
python3 scripts/fetch_transcript_pure_python.py --year 2026 --max 10

# Dry-run först
python3 scripts/fetch_transcript_pure_python.py --year 2026 --dry-run
```

**Om token är expired:** Scriptet refreshar automatiskt via `GetBearerToken`.

**METOD 2: Whisper (fallback för podcasts utan Apple transcript)**

För podcasts som saknar Apple transcript (t.ex. Gött Tjöt), använd Whisper:

```python
import subprocess

# Kör Whisper-transkribering för en podcast
podcast_id = "gotttjot"

whisper_result = subprocess.run([
    ".venv/bin/python", "-c", f'''
import json
from pathlib import Path
from podstock.rss.parser import get_latest_episodes
from podstock.rss.downloader import download_episode
from podstock.transcribe.whisper import transcribe, save_transcript

# Ladda podcast-config
with open("data/podcasts/sources.json") as f:
    sources = json.load(f)

podcast = next((p for p in sources["podcasts"] if p["id"] == "{podcast_id}"), None)
if not podcast or not podcast.get("rss_url"):
    print("ERROR: Ingen RSS-URL konfigurerad")
    exit(1)

# Hämta senaste episoder
episodes = get_latest_episodes(podcast["rss_url"], "{podcast_id}", n=5)

# Hitta episoder som saknar transkript
for ep in episodes:
    transcript_path = Path(f"data/transcripts/{podcast_id}") / f"{{ep.id}}.txt"
    if transcript_path.exists():
        continue

    print(f"Laddar ner audio: {{ep.title[:50]}}...")
    audio_dir = Path(f"data/temp_audio/{podcast_id}")
    audio_path = download_episode(ep, audio_dir, show_progress=False)

    print("Transkriberar med Whisper large-v3...")
    text = transcribe(audio_path, model="large-v3", language="sv")

    save_transcript(
        ep.id, text, Path("data/transcripts"), "{podcast_id}",
        metadata={{"source": "whisper", "model": "large-v3",
                  "original_title": ep.title,
                  "pub_date": ep.published_at.strftime("%Y-%m-%d")}}
    )
    print(f"✓ Transkriberat: {{ep.id}}")
'''
], capture_output=True, text=True, timeout=900)  # 15 min timeout
```

**WHISPER FÖRUTSÄTTNINGAR:**
- `mlx-whisper` installerat i venv
- Podcast måste ha `rss_url` konfigurerad i `data/podcasts/sources.json`
- Apple Silicon Mac (M1/M2/M3/M4)
- Ca 10-15 min per timme audio

### 2f. Verifiera nedladdning

**OBS:** `fetch_transcript_pure_python.py` extraherar automatiskt TTML till text.
Ingen separat extraktion behövs längre.

Verifiera att transcripts sparades:

```bash
# Kolla senaste transcripts
ls -lt data/transcripts/*/  | head -20

# Eller kör dry-run för att se vad som saknas
python3 scripts/fetch_transcript_pure_python.py --dry-run --year 2026
```

---

## Steg 3: Analyze Transcripts

### 3a. Valj analysmetod

**Kolla om OpenCode ar installerat:**

```bash
if [ -f "$HOME/.opencode/bin/opencode" ]; then
    ANALYZE_METHOD="opencode"
    echo "▸ Anvander OpenCode/GLM-4.7"
else
    ANALYZE_METHOD="claude"
    echo "▸ Anvander Claude Code (OpenCode ej installerat)"
fi
```

### 3b. Hitta oanalyserade transkript

```python
from pathlib import Path

# Hitta alla transkript (filtrera pa 2026+)
transcripts = set()
for podcast_dir in Path('data/transcripts').iterdir():
    if podcast_dir.is_dir():
        for f in podcast_dir.glob('*.txt'):
            if '-2026-' in f.stem or '-2025-' in f.stem:  # Senaste 2 aren
                transcripts.add(f.stem)

# Hitta redan analyserade (exkludera progress-filer)
analyzed = set()
for p in Path('data/podcasts/analyses-v2').glob('*-20??-??-??-????.json'):
    analyzed.add(p.stem)

# Filtrera oanalyserade
unanalyzed = sorted(transcripts - analyzed)

if not unanalyzed:
    print("✓ Alla transkript ar analyserade")
else:
    print(f"▸ {len(unanalyzed)} transkript att analysera")
```

### 3c. Kor analys

**Om Claude Code (rekommenderat for <10 transkript):**

```
Anropa analyze skill med Skill-verktyget:
Skill tool: skill="analyze"

Folj analyze skillens instruktioner for "Claude Code"-metoden.
```

**Om OpenCode/GLM-4.7 (for batch >10 transkript):**

```bash
# Generera ko-fil
echo "$unanalyzed_paths" > data/podcasts/analyses-v2/transcript-queue.txt

# Kor sekventiellt
for f in $(cat data/podcasts/analyses-v2/transcript-queue.txt); do
    python3 scripts/glm_driver.py "$f" data/podcasts/analyses-v2/
done
```

### 3d. Validera analyser

```python
from pathlib import Path
import json

# Validera att episode_id matchar filnamn
for f in Path('data/podcasts/analyses-v2').glob('*-20??-??-??-????.json'):
    try:
        data = json.loads(f.read_text())
        if data.get('episode_id') != f.stem:
            print(f"  ⚠ Mismatch: {f.name}")
            # Auto-fix
            data['episode_id'] = f.stem
            f.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        continue
```

---

## Steg 4: Sync Database

### 4a. Synka analyser

**VIKTIGT:** Anvand glob-filter for att undvika progress-filer.

```python
from pathlib import Path
import subprocess

# Hitta nya analysfiler (endast episode-analyser)
analysis_files = list(Path('data/podcasts/analyses-v2').glob('*-20??-??-??-????.json'))
print(f"▸ Synkar {len(analysis_files)} analysfiler...")

# Ladda varje fil individuellt for battre felhantering
for f in analysis_files:
    result = subprocess.run([
        ".venv/bin/python", "-m", "podstock", "db", "load",
        "--type", "podcast",
        "--file", str(f)
    ], capture_output=True, text=True)

    if "Loaded: 1" in result.stdout:
        pass  # Ny fil laddad
    elif "Skipped: 1" in result.stdout:
        pass  # Redan laddad
    else:
        print(f"  ⚠ {f.name}: {result.stderr[:50]}")

print("✓ Databas synkad")
```

### 4b. VERIFICATION GATE: DB Sync

**KRITISK:** Verifiera att sync faktiskt lyckades innan vi går vidare.

```python
import sqlite3
from pathlib import Path

def verify_db_sync():
    """Verifiera att databasen har rätt antal analyser."""

    # Räkna JSON-filer
    json_files = list(Path('data/podcasts/analyses-v2').glob('*-20??-??-??-????.json'))
    json_count = len(json_files)

    # Räkna DB-poster
    conn = sqlite3.connect('data/podstock.db')
    db_count = conn.execute(
        "SELECT COUNT(DISTINCT content_id) FROM analyses WHERE source_type='podcast'"
    ).fetchone()[0]
    conn.close()

    # Tillåt 5% diskrepans (för eventuella ogiltiga filer)
    if db_count < json_count * 0.95:
        print(f"⚠ VARNING: DB har {db_count} analyser men det finns {json_count} JSON-filer")
        print("  Kör: .venv/bin/python -m podstock db load --type podcast")
        return False

    print(f"✓ DB sync verifierad: {db_count} analyser")
    return True

# KÖR GATE
if not verify_db_sync():
    print("✗ DB SYNC GATE FAILED - åtgärda innan fortsättning")
    # Manuell intervention krävs
```

---

## Steg 5: Dashboard & Publish

### Generera dashboard

```bash
echo "▸ Genererar dashboard..."
.venv/bin/python -m podstock dashboard generate --no-embed

if [ $? -eq 0 ]; then
    echo "✓ Dashboard genererad"

    # VIKTIGT: Kopiera alla JSON-filer till rätt plats
    cp data/dashboard/data/*.json data/
    cp data/dashboard/index.html index.html
    cp -r data/dashboard/assets/* assets/
    echo "✓ Dashboard-filer kopierade"
else
    echo "✗ Dashboard misslyckades - STOPP"
    exit 1
fi
```

### 5b. VERIFICATION GATE: Filstorlekar

**KRITISK:** Verifiera att index.html är liten (--no-embed mode).

```python
from pathlib import Path

def verify_file_sizes():
    """Verifiera att inga filer överskrider Git-gränsen."""

    MAX_SIZES = {
        'index.html': 1_000_000,      # 1 MB max (--no-embed = ~150KB)
        'data/podcasts.json': 95_000_000,  # 95 MB varning
    }

    errors = []
    for file, max_size in MAX_SIZES.items():
        path = Path(file)
        if path.exists():
            size = path.stat().st_size
            if size > max_size:
                errors.append(f"{file}: {size/1_000_000:.1f}MB > {max_size/1_000_000:.1f}MB gräns")
            else:
                print(f"✓ {file}: {size/1_000_000:.1f}MB")

    if errors:
        print("✗ FILSTORLEK GATE FAILED:")
        for e in errors:
            print(f"  {e}")
        print("\n  FIX: Kör 'podstock dashboard generate --no-embed'")
        return False

    return True

# KÖR GATE
if not verify_file_sizes():
    print("STOPP - åtgärda filstorlekar")
```

### 5c. VERIFICATION GATE: Senaste analys finns i export

```python
import json
from pathlib import Path

def verify_latest_in_export():
    """Verifiera att senaste analysen finns i podcasts.json."""

    # Hitta senaste JSON-analysen
    json_files = sorted(
        Path('data/podcasts/analyses-v2').glob('*-20??-??-??-????.json'),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if not json_files:
        print("⚠ Inga analysfiler hittades")
        return True

    latest_file = json_files[0]
    latest_id = latest_file.stem

    # Kolla att den finns i exporten
    with open('data/podcasts.json') as f:
        data = json.load(f)

    episode_ids = [e.get('episode_id') for e in data.get('episodes', [])]

    if latest_id not in episode_ids:
        print(f"✗ Senaste analysen '{latest_id}' SAKNAS i podcasts.json!")
        print("  FIX: Kör DB sync + dashboard generate igen")
        return False

    print(f"✓ Senaste analysen finns i export: {latest_id}")
    return True

# KÖR GATE
if not verify_latest_in_export():
    print("STOPP - kör om pipeline")
```

### Git commit & push

```bash
echo "▸ Committar andringar..."

# Lägg till relevanta filer (index.html MÅSTE vara <1MB - verifierat av gate ovan)
git add \
    index.html \
    data/transcripts/ \
    data/podcasts/analyses-v2/*.json \
    data/*.json \
    assets/ \
    .claude/skills/

# Skapa commit
git commit -m "$(cat <<'EOF'
feat(data): sync podcast episodes

- Downloaded: ${N_DOWNLOADED} transcripts
- Analyzed: ${N_ANALYZED} episodes
- Recommendations: ${N_RECS} new

🤖 Generated with orchestrate-podcast-publish

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"

if [ $? -ne 0 ]; then
    echo "⚠ Inga andringar att committa"
else
    echo "▸ Pushar till origin..."
    git push origin main

    if [ $? -eq 0 ]; then
        echo "✓ Pushat - Vercel deploying"
    else
        echo "✗ Push misslyckades"
    fi
fi
```

---

## Steg 6: Korningsrapport

**VIKTIGT:** Visa ALLTID korningsrapport efter avslutad korning.

Anvand `OrchestrationReport` for strukturerad rapportering:

```python
from podstock.orchestration.report import OrchestrationReport

# Skapa rapport (populera under korningen)
report = OrchestrationReport()
report.model_used = selected_model  # "Claude" eller "GLM-4.7"

# Lagg till nedladdningar
for t in downloaded_transcripts:
    report.add_transcript(t["filename"], t["destination"], t["source"])

# Lagg till analyser
for a in completed_analyses:
    report.add_analysis(
        a["filename"],
        a["destination"],
        a["recommendations"],
        a["stock_segments"],
        a["insights"]
    )

# Lagg till timing
report.timing = {
    "Nedladdning": download_time,
    "Analys": analysis_time,
    "Databas-synk": sync_time,
    "Dashboard": dashboard_time,
}

# Visa i terminal
print(report.to_terminal())

# Spara till fil
saved_path = report.save()
print(f"\nRapport sparad: {saved_path}")
```

---

## Steg 7: Forbattringsforslag (Sjalvlakning)

**Efter korningsrapporten, om forbattringar observerats:**

```python
if report.improvements:
    print("\nFORBATTRINGSFORSLAG")
    for i, imp in enumerate(report.improvements, 1):
        print(f"  {i}. [{imp.category}] {imp.description}")
        print(f"     Forslag: {imp.suggested_fix}")

    # Fraga anvandaren med AskUserQuestion
    # Options: "Ja, atgarda alla", "Visa detaljer forst", "Nej, hoppa over"
else:
    print("\nInga forbattringar att foresla - allt ser bra ut!")
```

**Typer av forbattringar att observera under korning:**

| Observation | Kategori | Auto-fix |
|-------------|----------|----------|
| Insight med fel schema | quality | Ja |
| Saknad ticker-mappning | quality | Ja (lagg till i pending) |
| Timeout pa analys | optimization | Ja (oka timeout) |
| Schema-version <2.1 | critical | Ja (uppgradera) |
| Prompt-inkonsekvens | skill | Fraga forst |

**VIKTIGT:** Foresla ENDAST om det finns nagot tydligt att forbattra. Krysta inte fram feedback.

---

## Smart Feedback

Under korning, visa **minimal output** om allt gar bra:

```
▸ Pre-flight check...
▸ Found 3 unsynced episodes - asking user...
▸ Downloading 3 episodes...
▸ Analyzing 3 transcripts...
▸ Syncing database...
▸ Generating dashboard...
▸ Pushing to git...
✓ Done - website updated
```

---

## Felhantering

| Steg | Retry | Fallback | Vid fortsatt fel |
|------|-------|----------|------------------|
| Download | 3x | Apple → Whisper | Skip episode |
| Analyze | 3x | OpenCode → Claude | Skip transcript |
| DB Sync | 2x | - | Skip fil |
| Dashboard | 2x | - | **STOPP** |
| Git Push | 3x | - | **STOPP** |

---

## Trigger Phrases

- "synka allt"
- "kor hela pipelinen"
- "publicera podcasts"
- "uppdatera hemsidan"
- "orchestrate"
- `/orchestrate-podcast-publish`
