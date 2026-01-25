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

# 4. FetchTranscript binary (for Apple transcripts)
[ -f "tools/apple-transcripts/FetchTranscript" ] && echo "✓ FetchTranscript" || echo "⚠ FetchTranscript saknas"

# 5. Git status
git diff --quiet && echo "✓ Git working tree ren" || echo "⚠ Git har uncommitted changes"

# 6. Kolla analysmetod (OpenCode eller Claude)
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

**VIKTIGT:** Scriptet `download_apple_transcripts.py` stodjer BADE vara podcast-ID:n (t.ex. `marketmakers`) OCH Apple-namn (t.ex. `Market Makers`). Det oversatter automatiskt via `data/podcast_mapping.json`.

**OBS:** Scriptet använder automatiskt `osascript` workaround för att undvika
fork() crash med FetchTranscript. Ingen manuell åtgärd krävs.

**KOR:** Anropa podcast-download skill med Skill-verktyget:

```
Skill tool: skill="podcast-download"
```

Folj podcast-download skillens instruktioner for att ladda ner de valda avsnitten.

**Alternativt (om du vill kora inline):**

```python
# For varje valt avsnitt - anvand VARA podcast-ID:n (t.ex. "marketmakers")
for episode in selected_episodes:
    podcast_id = episode["podcast_id"]  # vara ID, t.ex. "marketmakers"

    # Forsok Apple Podcasts forst
    try:
        result = subprocess.run([
            "python3", "scripts/download_apple_transcripts.py",
            "--podcast", podcast_id,  # Scriptet oversatter till Apple-namn automatiskt
            "--max", "5"
        ], capture_output=True, text=True, timeout=120)

        if result.returncode == 0 and "Downloaded" in result.stdout:
            print(f"  ✓ {podcast_id} (Apple)")
            continue
    except:
        pass

    # Fallback till Whisper - KRÄVER RSS-URL konfigurerad i sources.json
    print(f"  ⚠ {podcast_id} - försöker Whisper...")

    # Kör Whisper-transkribering
    try:
        whisper_result = subprocess.run([
            ".venv/bin/python", "-c", f'''
import json
from pathlib import Path
from datetime import datetime
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

# Hitta rätt episod (senaste som saknar transkript)
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
    break
'''
        ], capture_output=True, text=True, timeout=900)  # 15 min timeout

        if whisper_result.returncode == 0:
            print(f"  ✓ {podcast_id} (Whisper)")
        else:
            print(f"  ✗ {podcast_id} Whisper misslyckades: {whisper_result.stderr[:100]}")
    except subprocess.TimeoutExpired:
        print(f"  ✗ {podcast_id} Whisper timeout (>15 min)")
    except Exception as e:
        print(f"  ✗ {podcast_id} Whisper fel: {e}")
```

**WHISPER FÖRUTSÄTTNINGAR:**
- `mlx-whisper` installerat i venv
- Podcast måste ha `rss_url` konfigurerad i `data/podcasts/sources.json`
- Apple Silicon Mac (M1/M2/M3/M4)
- Ca 10-15 min per timme audio

### 2f. Extrahera TTML till text

**VIKTIGT:** Efter nedladdning maste TTML-filer extraheras till textfiler.

```python
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Paths
APPLE_DB = Path.home() / "Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Documents/MTLibrary.sqlite"
TTML_CACHE = Path.home() / "Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Library/Cache/Assets/TTML"
TRANSCRIPTS_DIR = Path("data/transcripts")
PODCAST_MAPPING = Path("data/podcast_mapping.json")
COCOA_EPOCH = datetime(2001, 1, 1)

# Load podcast mapping
with open(PODCAST_MAPPING) as f:
    apple_to_id = json.load(f).get("apple_to_id", {})

def find_ttml_file(transcript_id: str):
    potential = TTML_CACHE / transcript_id
    if potential.exists():
        return potential
    match = re.search(r'transcript_(\d+)\.ttml$', transcript_id)
    if match:
        ttml_id = match.group(1)
        alt_path = TTML_CACHE / transcript_id.replace(f"transcript_{ttml_id}.ttml", f"transcript_{ttml_id}.ttml-{ttml_id}.ttml")
        if alt_path.exists():
            return alt_path
    return None

def parse_ttml(ttml_path):
    raw = ttml_path.read_text(encoding="utf-8")
    words = re.findall(r'podcasts:unit="word"[^>]*>([^<]+)</span>', raw)
    return re.sub(r"\s+", " ", " ".join(w.strip() for w in words if w.strip()))

# Query and extract
conn = sqlite3.connect(APPLE_DB)
cursor = conn.cursor()
cursor.execute("""
    SELECT e.ZTITLE, p.ZTITLE, e.ZPUBDATE, e.ZTRANSCRIPTIDENTIFIER
    FROM ZMTEPISODE e JOIN ZMTPODCAST p ON e.ZPODCAST = p.Z_PK
    WHERE e.ZTRANSCRIPTIDENTIFIER IS NOT NULL ORDER BY e.ZPUBDATE DESC
""")

extracted = 0
for row in cursor.fetchall():
    episode_title, podcast_name, pub_date_cocoa, transcript_id = row
    podcast_id = apple_to_id.get(podcast_name)
    if not podcast_id:
        continue

    ttml_path = find_ttml_file(transcript_id)
    if not ttml_path:
        continue

    pub_date = COCOA_EPOCH + timedelta(seconds=pub_date_cocoa)
    episode_id = f"{podcast_id}-{pub_date.strftime('%Y-%m-%d')}-{hashlib.md5(episode_title.encode()).hexdigest()[:4]}"

    transcript_path = TRANSCRIPTS_DIR / podcast_id / f"{episode_id}.txt"
    if transcript_path.exists():
        continue

    text = parse_ttml(ttml_path)
    if len(text.split()) < 100:
        continue

    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    header = f"{'='*60}\nEpisode: {episode_id}\nPodcast: {podcast_id}\nsource: apple\noriginal_title: {episode_title}\npub_date: {pub_date.strftime('%Y-%m-%d')}\n{'='*60}\n\n"
    transcript_path.write_text(header + text + "\n")
    print(f"  + {episode_id}")
    extracted += 1

conn.close()
print(f"✓ Extracted: {extracted} new transcripts")
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
