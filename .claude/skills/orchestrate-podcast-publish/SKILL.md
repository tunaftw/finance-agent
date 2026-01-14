---
name: orchestrate-podcast-publish
description: Master orchestration skill som kor hela pipelinen fran nya podcast-avsnitt till publicerad hemsida. Anvand nar anvandaren sager "synka allt", "publicera podcasts", "kor hela pipelinen", eller vill uppdatera hemsidan med senaste analyserna.
---

# Orchestrate Podcast Publish

Kor hela pipelinen: download -> analyze -> sync DB -> publish hemsida.

## Quick Start

1. **Pre-flight check** - Validera miljo
2. **Download** - Hamta nya transkript (Apple/Whisper)
3. **Analyze** - Analysera med OpenCode/GLM-4.7
4. **Sync DB** - Ladda analyser + priser till databas
5. **Publish** - Generera dashboard, commit, push -> Vercel

## Hardkodade Variden

```
year_filter:        CURRENT_YEAR  # Dynamiskt - anvand datetime.now().year
retry_attempts:     3             # Max retry-forsok
whisper_timeout:    15 min        # Timeout for Whisper
analysis_model:     glm-4.7       # Modell for batch-analys
parallel_agents:    3             # Antal parallella agenter for analys
analysis_timeout:   180 sec       # Timeout per transkript-analys
```

**VIKTIGT:** year_filter bor aldrig vara hardkodat till ett specifikt ar. Anvand alltid `datetime.now().year` for att filtrera pa innevarande ar.

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
[ -f "data/podstock.db" ] && echo "✓ Database" || echo "✗ podstock.db saknas - kor 'podstock db init'"

# 4. FetchTranscript binary (for Apple transcripts)
[ -f "tools/apple-transcripts/FetchTranscript" ] && echo "✓ FetchTranscript" || echo "⚠ FetchTranscript saknas - Apple transcripts disabled"

# 5. Git status
git diff --quiet && echo "✓ Git working tree ren" || echo "⚠ Git har uncommitted changes"
```

**VIKTIGT: Absoluta sokvagar**
- Alla scripts MASTE koras fran projekt-root (`/Users/.../Finance-agent/`)
- Undvik `cd` till subdirectories innan scripts kors
- Anvand absoluta sokvagar i Python-kod: `Path(__file__).parent.parent / "data/..."`
- Om du maste anvanda `cd`, aterstall working directory efterat

**Om nagot kritiskt saknas:** STOPP och meddela anvandaren.

**Om git har uncommitted changes:** Fraga anvandaren om de vill fortsatta anda eller committa forst.

---

## Steg 2: Download Transcripts

Anropa **podcast-download** skill-logiken:

```python
import subprocess
from pathlib import Path
from datetime import datetime

# Anvand innevarande ar (ALDRIG hardkoda!)
current_year = str(datetime.now().year)

# Kolla sync status
result = subprocess.run(
    ["python3", "scripts/podcast/check_sync_status.py", "--year", current_year, "--json"],
    capture_output=True, text=True
)

import json
status = json.loads(result.stdout)
unsynced = status.get("missing_episodes", [])

if not unsynced:
    print("✓ Alla podcasts ar synkade")
else:
    print(f"▸ Hittat {len(unsynced)} osynkade avsnitt")
```

### For varje osynkat avsnitt:

```python
downloaded = []
failed = []

for episode in unsynced:
    success = False

    # Forsok 1: Apple Podcasts transcript
    for attempt in range(3):
        try:
            transcript = fetch_apple_transcript(episode)
            save_transcript(episode, transcript)
            downloaded.append({"episode": episode, "method": "apple"})
            success = True
            break
        except NotFound:
            break  # Ga till Whisper
        except Error as e:
            if attempt < 2:
                print(f"  ⚠ Retry {attempt+1}/3...")
                continue

    # Forsok 2: Whisper (om Apple misslyckades)
    if not success:
        for attempt in range(3):
            try:
                transcript = whisper_transcribe(episode, timeout=15*60)
                save_transcript(episode, transcript)
                downloaded.append({"episode": episode, "method": "whisper"})
                success = True
                break
            except Error as e:
                if attempt < 2:
                    print(f"  ⚠ Whisper retry {attempt+1}/3...")
                    continue

    if not success:
        failed.append(episode)
        print(f"  ✗ {episode['id']} - skippas")
```

**Output:** Visa sammanfattning av nedladdade transkript.

---

## Steg 3: Analyze Transcripts

Anropa **analyze** skill-logiken (batch mode med OpenCode/GLM-4.7):

### Generera ko-fil

```python
from pathlib import Path

# Hitta alla transkript
transcripts = set()
for podcast_dir in Path('data/transcripts').iterdir():
    if podcast_dir.is_dir():
        transcripts.update(p.stem for p in podcast_dir.glob('*.txt'))

# Hitta redan analyserade
analyzed = set()
for p in Path('data/podcasts/analyses-v2').glob('*.json'):
    analyzed.add(p.stem)

# Filtrera oanalyserade
unanalyzed = [t for t in transcripts if t not in analyzed]

if not unanalyzed:
    print("✓ Alla transkript ar analyserade")
else:
    # Skriv ko-fil
    queue_file = Path('data/podcasts/analyses-v2/transcript-queue.txt')

    # Hitta fulla sokvagar
    queue_paths = []
    for stem in unanalyzed:
        for podcast_dir in Path('data/transcripts').iterdir():
            if podcast_dir.is_dir():
                for f in podcast_dir.glob(f'{stem}.txt'):
                    queue_paths.append(str(f))

    queue_file.write_text('\n'.join(sorted(queue_paths)))
    print(f"▸ {len(unanalyzed)} transkript att analysera")
```

### Kor PARALLELL analys (rekommenderat for >10 transkript)

Om fler an 10 transkript ska analyseras, anvand parallella agenter for ~3x speedup:

```python
from pathlib import Path

# Dela upp transkript i N grupper (default: 3 agenter)
N_AGENTS = 3
chunk_size = (len(unanalyzed) + N_AGENTS - 1) // N_AGENTS

groups = []
for i in range(N_AGENTS):
    start = i * chunk_size
    end = min(start + chunk_size, len(unanalyzed))
    if start < len(unanalyzed):
        groups.append(unanalyzed[start:end])

# Skapa ko-filer per agent
queue_dir = Path('data/podcasts/analyses-v2/parallel-queues')
queue_dir.mkdir(parents=True, exist_ok=True)

for i, group in enumerate(groups, 1):
    queue_file = queue_dir / f'queue-agent-{i}.txt'
    queue_file.write_text('\n'.join(group))
    print(f"Agent {i}: {len(group)} transkript")
```

**Starta agenter parallellt med Task-verktyget:**

```
Starta 3 Task-agenter (subagent_type=general-purpose, run_in_background=true)
varje agent far:
  - Sin ko-fil (queue-agent-N.txt)
  - Instruktion att kora: python3 scripts/glm_driver.py <path> data/podcasts/analyses-v2/
  - Rapportera: lyckade, misslyckade, total tid
```

**Overvaka och samla resultat:**
- Anvand TaskOutput med block=false for att kolla progress
- Vantar tills alla agenter rapporterat klart
- Sammanstall resultat i slutrapporten

### Fallback: Sekventiell batch (for <10 transkript)

```bash
# For fa transkript, kor direkt utan parallellisering
for f in $(cat data/podcasts/analyses-v2/transcript-queue.txt); do
    python3 scripts/glm_driver.py "$f" data/podcasts/analyses-v2/
done
```

### Kanda problem

| Problem | Losning |
|---------|---------|
| Transkript hanger (>180 sec) | Skip efter timeout, logga for manuell review |
| GLM rate limit | Automatisk retry efter 30 sek |
| Agent crashar | Andra agenter fortsatter, rapportera skippade |
| Episode ID/filnamn mismatch | Validera att JSON `episode_id` matchar filnamnet |
| podcasts.json ur synk | Kopiera `data/dashboard/data/podcasts.json` → `data/podcasts.json` |
| Duplicerade DB-entries | Kor `sqlite3 data/podstock.db` och rensa manuellt |

### Validering efter analys

Efter att analyser skapats, validera att `episode_id` inuti JSON matchar filnamnet:

```python
from pathlib import Path
import json

def validate_episode_ids():
    """Validera att episode_id matchar filnamn."""
    mismatches = []
    for f in Path('data/podcasts/analyses-v2').glob('*.json'):
        try:
            data = json.loads(f.read_text())
            episode_id = data.get('episode_id', '')
            if episode_id and episode_id != f.stem:
                mismatches.append({
                    'file': f.name,
                    'file_stem': f.stem,
                    'episode_id': episode_id
                })
        except:
            continue

    if mismatches:
        print(f"⚠ {len(mismatches)} episode_id/filnamn-mismatcher:")
        for m in mismatches[:5]:
            print(f"  {m['file']}: har episode_id='{m['episode_id']}'")
    else:
        print("✓ Alla episode_id matchar filnamn")

    return mismatches
```

**Om mismatch hittas:** Uppdatera `episode_id` i JSON-filen till att matcha filnamnet.

---

## Steg 4: Sync Database

### Synka analyser (database-analyze-sync)

```python
from pathlib import Path
import subprocess

# Kolla vad som behover synkas
result = subprocess.run(
    ["python3", "-c", """
from pathlib import Path
import hashlib
import sqlite3

db_path = Path('data/podstock.db')
conn = sqlite3.connect(db_path)
cursor = conn.execute("SELECT file_path, file_hash FROM load_log WHERE status IN ('success', 'skipped')")
loaded = {row[0]: row[1] for row in cursor.fetchall()}

podcast_files = list(Path('data/podcasts/analyses-v2').glob('*.json'))
new_count = sum(1 for f in podcast_files if str(f.absolute()) not in loaded)
print(new_count)
"""],
    capture_output=True, text=True
)

new_analyses = int(result.stdout.strip())

if new_analyses == 0:
    print("✓ Databasen ar up-to-date")
else:
    print(f"▸ Synkar {new_analyses} nya analyser...")
    subprocess.run(["podstock", "db", "load"], check=True)
    print("✓ Databas synkad")
```

### Synka priser (price-sync, endast lokalt)

```python
# Synka priser fran lokalt bibliotek (INGA Yahoo API-anrop)
subprocess.run([
    "python3", "-c", """
from podstock.db.engine import get_session
from podstock.db.models import Recommendation, RecommendationPerformance, Price, Security

session = get_session()

# Hitta recs utan prisdata
recs_without = session.query(Recommendation).outerjoin(
    RecommendationPerformance
).filter(RecommendationPerformance.id == None).all()

synced = 0
missing_tickers = []

for rec in recs_without:
    # Forsok hitta pris i lokalt bibliotek
    security = session.query(Security).filter(
        Security.name == rec.stock_name
    ).first()

    if security:
        price = session.query(Price).filter(
            Price.security_id == security.id,
            Price.date <= rec.date
        ).order_by(Price.date.desc()).first()

        if price:
            perf = RecommendationPerformance(
                recommendation_id=rec.id,
                price_at_rec=price.close
            )
            session.add(perf)
            synced += 1
        else:
            missing_tickers.append(rec.stock_name)
    else:
        missing_tickers.append(rec.stock_name)

session.commit()
print(f'Synced: {synced}, Missing: {len(set(missing_tickers))}')
"""
], check=True)
```

**Om tickers saknar prishistorik:** Logga for slutrapporten, fortsatt.

---

## Steg 5: Dashboard & Publish

### Generera dashboard

```bash
echo "▸ Genererar dashboard..."
podstock dashboard generate --no-embed

if [ $? -eq 0 ]; then
    echo "✓ Dashboard genererad"

    # VIKTIGT: Kopiera podcasts.json till rätt plats
    # Dashboard genererar till data/dashboard/data/podcasts.json
    # men webbappen laddar från data/podcasts.json
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

# Lagg till alla relevanta filer
git add \
    data/transcripts/ \
    data/podcasts/analyses-v2/ \
    data/podstock.db \
    data/*.json \
    index.html \
    assets/ \
    .claude/skills/ \
    logs/orchestration/

# Skapa commit-meddelande
COMMIT_MSG="feat(data): sync podcast episodes

- Downloaded: ${N_DOWNLOADED} transcripts
- Analyzed: ${N_ANALYZED} episodes
- Recommendations: ${N_RECS} new

🤖 Generated with orchestrate-podcast-publish"

git commit -m "$COMMIT_MSG"

if [ $? -ne 0 ]; then
    echo "⚠ Inga andringar att committa"
else
    echo "▸ Pushar till origin..."
    git push origin main

    if [ $? -eq 0 ]; then
        echo "✓ Pushat - Vercel deploying"
    else
        echo "✗ Push misslyckades - STOPP"
        exit 1
    fi
fi
```

---

## Steg 6: Slutrapport

Generera och spara slutrapport:

```python
from datetime import datetime
from pathlib import Path

timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
report_path = Path(f"logs/orchestration/{timestamp}.md")
latest_path = Path("logs/orchestration/latest.md")

report = f"""
════════════════════════════════════════════════════════════════════
ORCHESTRATE-PODCAST-PUBLISH COMPLETE
════════════════════════════════════════════════════════════════════

RESULTAT
────────
✓ Downloaded:  {n_downloaded} transcripts ({n_apple} Apple, {n_whisper} Whisper)
✓ Analyzed:    {n_analyzed} episodes → {n_recs} recommendations
✓ DB synced:   {n_synced_analyses} analyses, {n_synced_recs} recs
✓ Prices:      {n_prices_matched}/{n_total_recs} recs matched
✓ Published:   Commit {git_hash} pushed → Vercel deploying

SJALVFORRATTRINGAR
──────────────────
{improvements_text or '(inga)'}

SKIPPADE (kraver manuell atgard)
────────────────────────────────
{skipped_text or '(inga)'}

TIMING
──────
Total tid:     {total_time}
  Download:    {download_time}
  Analyze:     {analyze_time}
  Sync:        {sync_time}
  Publish:     {publish_time}

════════════════════════════════════════════════════════════════════
"""

report_path.write_text(report)
latest_path.write_text(report)

print(report)
```

---

## Smart Feedback

Under korning, visa **minimal output** om allt gar bra:

```
▸ Pre-flight check...
▸ Downloading 3 episodes...
▸ Analyzing 3 transcripts...
▸ Syncing database...
▸ Generating dashboard...
▸ Pushing to git...
✓ Done - website updated
```

Vid problem, visa **detaljerad output**:

```
▸ Downloading 3 episodes...
  ⚠ fillorkill-2026-01-09: Apple transcript not found
    → Retry 1/2 with Whisper...
    → Retry 2/2 with Whisper...
    ✓ Whisper succeeded (took 4m 32s)
```

---

## Sjalvforbattring

Under korningen, overvaka for kanda problem. Se [references/improvement-rules.md](references/improvement-rules.md).

**Fixar autonomt:**
- Sokvagsproblem i skills
- Saknade podcast mappings
- Felaktiga script-anrop

**Rapporterar i slutet:** Alla gjorda forbattringar listas i slutrapporten.

---

## Felhantering

| Steg | Retry | Fallback | Vid fortsatt fel |
|------|-------|----------|------------------|
| Download | 3x | Apple → Whisper | Skip episode |
| Analyze | 3x | - | Skip transcript |
| DB Sync | 2x | - | Skip fil |
| Price Sync | - | Endast lokalt | Logga saknade |
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
