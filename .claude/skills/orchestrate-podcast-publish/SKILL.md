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

**Anvand AskUserQuestion:**

```
Fraga: "{X} avsnitt saknar transkript. Vad vill du gora?"

Options:
1. "Ladda ner alla {X}" - Kör hela listan
2. "Valj specifika podcasts" - Visa multiselect med podcast-namn
3. "Hoppa over nedladdning" - Ga direkt till analys
```

Om anvandaren valjer "Valj specifika", anvand multiSelect=true med podcast-namn.

### 2c. Ladda ner valda transkript

**KOR:** Anropa podcast-download skill med Skill-verktyget:

```
Skill tool: skill="podcast-download"
```

Folj podcast-download skillens instruktioner for att ladda ner de valda avsnitten.

**Alternativt (om du vill kora inline):**

```python
# For varje valt avsnitt
for episode in selected_episodes:
    # Forsok Apple Podcasts forst
    try:
        result = subprocess.run([
            "python3", "scripts/download_apple_transcripts.py",
            "--podcast", episode["podcast"],
            "--max", "1"
        ], capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            print(f"  ✓ {episode['id']} (Apple)")
            continue
    except:
        pass

    # Fallback till Whisper
    print(f"  ⚠ {episode['id']} - kraver Whisper (manuell atgard)")
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

---

## Steg 5: Dashboard & Publish

### Generera dashboard

```bash
echo "▸ Genererar dashboard..."
.venv/bin/python -m podstock dashboard generate --no-embed

if [ $? -eq 0 ]; then
    echo "✓ Dashboard genererad"

    # VIKTIGT: Kopiera podcasts.json till ratt plats
    cp data/dashboard/data/podcasts.json data/podcasts.json
    echo "✓ podcasts.json synkad"
else
    echo "✗ Dashboard misslyckades - STOPP"
    exit 1
fi
```

### Git commit & push

```bash
echo "▸ Committar andringar..."

# Lagg till relevanta filer
git add \
    data/transcripts/ \
    data/podcasts/analyses-v2/*.json \
    data/podcasts.json \
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

## Steg 6: Slutrapport

Visa sammanfattning:

```
════════════════════════════════════════════════════════════════════
ORCHESTRATE-PODCAST-PUBLISH COMPLETE
════════════════════════════════════════════════════════════════════

RESULTAT
────────
✓ Downloaded:  {n_downloaded} transcripts ({n_apple} Apple, {n_whisper} Whisper)
✓ Analyzed:    {n_analyzed} episodes → {n_recs} recommendations
✓ DB synced:   {n_synced} analyses loaded
✓ Published:   Commit {git_hash} pushed → Vercel deploying

════════════════════════════════════════════════════════════════════
```

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
