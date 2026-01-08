---
name: database-analyze-sync
description: Synka JSON-analysfiler till SQLite-databasen. Anvand nar anvandaren fragar "synka databasen", "uppdatera databasen", "ladda analyser", eller vill kontrollera vad som saknas i databasen. Visar sync-status och synkar inkrementellt. (project)
---

# Database Analyze Sync Skill

Synkronisera JSON-analysfiler fran podcasts, Twitter och YouTube till podstock.db.

## Quick Start

1. **Visa sync-status** - Vad ar osynkat per kalla (kors FORST)
2. Om allt synkat: Visa "Databasen ar up-to-date!"
3. Om osynkat: Fraga anvandaren vad de vill synka
4. Kor inkrementell sync
5. Visa sammanfattning

## Step 1: Check Sync Status (Kor ALLTID forst)

Kolla automatiskt vad som behover synkas:

```python
from pathlib import Path
import hashlib
import sqlite3

def get_sync_status():
    """Returnerar sync-status per kalla."""
    db_path = Path("data/podstock.db")

    if not db_path.exists():
        return {"error": "Database not found. Run 'podstock db init' first."}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Hamta alla laddade filer (bade success och skipped = redan processade)
    cursor = conn.execute("""
        SELECT file_path, file_hash
        FROM load_log
        WHERE status IN ('success', 'skipped')
    """)
    loaded = {row['file_path']: row['file_hash'] for row in cursor.fetchall()}

    status = {}

    # Podcasts - kolla data/podcasts/analyses-v2/
    # OBS: Anvand absoluta sokvagar for att matcha load_log
    podcast_files = list(Path("data/podcasts/analyses-v2").glob("*.json"))
    podcast_new = []
    podcast_modified = []
    for f in podcast_files:
        file_hash = hashlib.sha256(f.read_bytes()).hexdigest()
        path_str = str(f.absolute())  # Absolut sokvag (matchar loader.py)
        if path_str not in loaded:
            podcast_new.append(f.name)
        elif loaded[path_str] != file_hash:
            podcast_modified.append(f.name)
    status['podcasts'] = {
        'total_files': len(podcast_files),
        'new': len(podcast_new),
        'modified': len(podcast_modified),
        'synced': len(podcast_files) - len(podcast_new) - len(podcast_modified),
        'new_examples': podcast_new[:5],
        'modified_examples': podcast_modified[:3]
    }

    # Twitter - kolla data/twitter/analyses/
    twitter_files = list(Path("data/twitter/analyses").glob("*-tweet-analyses.json"))
    twitter_new = []
    twitter_modified = []
    for f in twitter_files:
        file_hash = hashlib.sha256(f.read_bytes()).hexdigest()
        path_str = str(f.absolute())  # Absolut sokvag (matchar loader.py)
        if path_str not in loaded:
            twitter_new.append(f.name)
        elif loaded[path_str] != file_hash:
            twitter_modified.append(f.name)
    status['twitter'] = {
        'total_files': len(twitter_files),
        'new': len(twitter_new),
        'modified': len(twitter_modified),
        'synced': len(twitter_files) - len(twitter_new) - len(twitter_modified),
        'new_examples': twitter_new[:5],
        'modified_examples': twitter_modified[:3]
    }

    # YouTube - kolla data/youtube/analyses/
    youtube_dir = Path("data/youtube/analyses")
    youtube_files = [f for f in youtube_dir.glob("*.json")
                    if not f.stem.endswith("-analysis")] if youtube_dir.exists() else []
    youtube_new = []
    youtube_modified = []
    for f in youtube_files:
        file_hash = hashlib.sha256(f.read_bytes()).hexdigest()
        path_str = str(f.absolute())  # Absolut sokvag (matchar loader.py)
        if path_str not in loaded:
            youtube_new.append(f.name)
        elif loaded[path_str] != file_hash:
            youtube_modified.append(f.name)
    status['youtube'] = {
        'total_files': len(youtube_files),
        'new': len(youtube_new),
        'modified': len(youtube_modified),
        'synced': len(youtube_files) - len(youtube_new) - len(youtube_modified),
        'new_examples': youtube_new[:5],
        'modified_examples': youtube_modified[:3]
    }

    conn.close()
    return status

# Kor och visa status
status = get_sync_status()
if 'error' in status:
    print(f"ERROR: {status['error']}")
else:
    print("=" * 60)
    print("DATABASE SYNC STATUS")
    print("=" * 60)
    total_pending = 0
    for source, data in status.items():
        pending = data['new'] + data['modified']
        total_pending += pending
        emoji = "OK" if pending == 0 else "SYNC"
        print(f"\n[{emoji}] {source.upper()}")
        print(f"    Filer: {data['total_files']} totalt, {data['synced']} synkade")
        if data['new'] > 0:
            print(f"    Nya: {data['new']} st")
            if data['new_examples']:
                examples = ', '.join(data['new_examples'][:3])
                print(f"         Ex: {examples}...")
        if data['modified'] > 0:
            print(f"    Andrade: {data['modified']} st")
    print("\n" + "=" * 60)
    if total_pending == 0:
        print("DATABASEN AR UP-TO-DATE!")
    else:
        print(f"TOTALT: {total_pending} filer behover synkas")
    print("=" * 60)
```

**Output-exempel:**
```
============================================================
DATABASE SYNC STATUS
============================================================

[SYNC] PODCASTS
    Filer: 3151 totalt, 1919 synkade
    Nya: 1232 st
         Ex: borspodden-2025-01-15.json, fillorkill-2025-01-14.json...

[OK] TWITTER
    Filer: 2 totalt, 2 synkade

[SYNC] YOUTUBE
    Filer: 273 totalt, 228 synkade
    Nya: 45 st
============================================================
TOTALT: 1277 filer behover synkas
============================================================
```

## Step 2: User Selection

Om det finns filer att synka, fraga anvandaren med AskUserQuestion:

```
Vad vill du gora?
1. Synka alla (1277 st) - Recommended
2. Endast podcasts (1232 st)
3. Endast twitter (0 st)
4. Endast youtube (45 st)
5. Avbryt
```

## Step 3: Execute Sync

Se [references/sync-method.md](references/sync-method.md) for detaljerad implementation.

**Kort sammanfattning:**
- Anvander befintliga loaders fran `podstock.db.loader`
- En transaktion per fil (isolerad rollback vid fel)
- Progress visas var 50:e fil
- Idempotent via load_log + content_hash

## Step 4: Completion Summary

```
============================================================
SYNC KLAR
============================================================

Synkade: 1275/1277 filer
  - Podcasts: 1230/1232
  - Twitter: 0/0
  - YouTube: 45/45

Misslyckades: 2 filer
  - aktiepodden-invalid.json: Invalid JSON
  - borspodden-empty.json: Missing episode_id

Nya i databasen:
  - 1275 analyser
  - 4532 rekommendationer
  - 156 pending securities (for manuell mapping)

Tips: Kor 'podstock db pending list' for att se omatchade aktienamn
============================================================
```

## Source Locations

| Kalla | JSON-filer | Mapp |
|-------|------------|------|
| Podcasts | `{podcast_id}-{date}-{hash}.json` | `data/podcasts/analyses-v2/` |
| Twitter | `{handle}-tweet-analyses.json` | `data/twitter/analyses/` |
| YouTube | `{video_id}.json` | `data/youtube/analyses/` |

## Database Tables Affected

| Tabell | Beskrivning |
|--------|-------------|
| `sources` | Podcast/Twitter/YouTube-kallor |
| `content` | Episodes/tweets/videos |
| `analyses` | Versionerade analyser |
| `recommendations` | Aktierekommendationer |
| `mentions` | Crypto-omnamnanden |
| `key_takeaways` | Nyckelinsikter |
| `pending_securities` | Omatchade aktienamn |
| `load_log` | Sparar fil+hash for idempotens |

## Idempotency

Synken ar idempotent:
- Filer med samma hash laddas inte om (load_log)
- Analyser med samma content_hash skapas inte dubbelt
- Nya versioner av analyser far nytt versionsnummer
- Ingen data duplikeras

## Error Handling

| Fel | Losning |
|-----|---------|
| `Database not found` | Kor `podstock db init` forst |
| `Invalid JSON` | Logga fel, hoppa over fil, fortsatt |
| `Missing episode_id` | Logga fel, hoppa over fil |
| `Database locked` | Forsok igen efter 1 sekund |
| `Partial failure` | Rollback per fil, fortsatt med nasta |

## Relaterade Kommandon

```bash
# Visa databasstatus
podstock db status

# Lista omatchade aktier
podstock db pending list

# Sok rekommendationer
podstock db search Evolution

# Manuell laddning (om nodvandigt)
podstock db load --type podcast --file path/to/file.json
```
