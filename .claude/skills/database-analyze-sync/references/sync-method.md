# Sync Method - Detaljerad Implementation

## Overview

Synk-metoden anvander de befintliga loaders i `src/podstock/db/loader.py`:
- `PodcastLoader` - for podcast-analyser
- `TwitterLoader` - for Twitter-analyser
- `YouTubeLoader` - for YouTube-analyser

## Full Sync Implementation

```python
from pathlib import Path
from podstock.db.engine import get_engine, get_session
from podstock.db.loader import PodcastLoader, TwitterLoader, YouTubeLoader

def sync_all(source_types: list[str] = None, verbose: bool = True):
    """
    Synka JSON-filer till databasen.

    Args:
        source_types: Lista med kallor att synka ['podcast', 'twitter', 'youtube']
                     Om None synkas alla kallor
        verbose: Visa progress

    Returns:
        dict med resultat per kalla
    """
    if source_types is None:
        source_types = ['podcast', 'twitter', 'youtube']

    engine = get_engine()
    results = {}

    for source_type in source_types:
        if source_type == 'podcast':
            results['podcast'] = sync_source(
                engine=engine,
                loader=PodcastLoader(),
                data_dir=Path("data/podcasts/analyses-v2"),
                pattern="*.json",
                source_name="podcasts",
                verbose=verbose
            )
        elif source_type == 'twitter':
            results['twitter'] = sync_source(
                engine=engine,
                loader=TwitterLoader(),
                data_dir=Path("data/twitter/analyses"),
                pattern="*-tweet-analyses.json",
                source_name="twitter",
                verbose=verbose
            )
        elif source_type == 'youtube':
            results['youtube'] = sync_source(
                engine=engine,
                loader=YouTubeLoader(),
                data_dir=Path("data/youtube/analyses"),
                pattern="*.json",
                source_name="youtube",
                verbose=verbose,
                exclude_suffix="-analysis"  # Hoppa over -analysis.json varianter
            )

    return results


def sync_source(
    engine,
    loader,
    data_dir: Path,
    pattern: str,
    source_name: str,
    verbose: bool = True,
    exclude_suffix: str = None
) -> dict:
    """
    Synka en specifik kalla till databasen.

    Returns:
        dict med {loaded, skipped, failed, errors, new_recommendations}
    """
    if not data_dir.exists():
        return {
            "loaded": 0,
            "skipped": 0,
            "failed": 0,
            "errors": [],
            "new_recommendations": 0,
            "message": f"Directory not found: {data_dir}"
        }

    # Hitta alla JSON-filer
    files = sorted(data_dir.glob(pattern))

    # Filtrera bort filer med specifik suffix
    if exclude_suffix:
        files = [f for f in files if not f.stem.endswith(exclude_suffix)]

    if not files:
        return {
            "loaded": 0,
            "skipped": 0,
            "failed": 0,
            "errors": [],
            "new_recommendations": 0,
            "message": f"No files found in {data_dir}"
        }

    results = {
        "loaded": 0,
        "skipped": 0,
        "failed": 0,
        "errors": [],
        "new_recommendations": 0
    }

    total = len(files)
    if verbose:
        print(f"\nSynkar {source_name}: {total} filer...")

    for i, json_path in enumerate(files, 1):
        try:
            # Anvand separat session per fil for isolerad rollback
            with get_session(engine) as session:
                result = loader.load(json_path, session)

                if result.status == "success":
                    results["loaded"] += 1
                    results["new_recommendations"] += result.recommendations_count
                    if verbose and i % 50 == 0:
                        print(f"  [{i}/{total}] Laddade {results['loaded']} filer...")
                elif result.status == "skipped":
                    results["skipped"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append((json_path.name, result.error))
                    if verbose:
                        print(f"  [!] {json_path.name}: {result.error}")

        except Exception as e:
            results["failed"] += 1
            results["errors"].append((json_path.name, str(e)))
            if verbose:
                print(f"  [ERROR] {json_path.name}: {e}")

    if verbose:
        print(f"  Klart: {results['loaded']} laddade, {results['skipped']} hoppade over, {results['failed']} fel")

    return results


def print_sync_summary(results: dict):
    """Skriv ut sammanfattning av sync."""
    print("\n" + "=" * 60)
    print("SYNC KLAR")
    print("=" * 60)

    total_loaded = sum(r.get('loaded', 0) for r in results.values())
    total_failed = sum(r.get('failed', 0) for r in results.values())
    total_recs = sum(r.get('new_recommendations', 0) for r in results.values())

    print(f"\nSynkade filer:")
    for source, data in results.items():
        loaded = data.get('loaded', 0)
        failed = data.get('failed', 0)
        total = loaded + data.get('skipped', 0) + failed
        status = "OK" if failed == 0 else "!"
        print(f"  [{status}] {source.capitalize()}: {loaded}/{total}")

    if total_failed > 0:
        print(f"\nMisslyckades: {total_failed} filer")
        for source, data in results.items():
            for filename, error in data.get('errors', [])[:5]:
                print(f"  - {filename}: {error}")

    print(f"\nNya poster:")
    print(f"  - {total_loaded} analyser")
    print(f"  - {total_recs} rekommendationer")
    print("=" * 60)
```

## Snabb Sync (Endast nya filer)

For att bara synka filer som inte redan ar laddade:

```python
import hashlib
import sqlite3

def get_unsynced_files(source_type: str) -> list[Path]:
    """Returnera lista med osynkade filer for en kalla."""
    db_path = Path("data/podstock.db")
    conn = sqlite3.connect(db_path)

    # Hamta redan laddade filer
    cursor = conn.execute("""
        SELECT file_path, file_hash
        FROM load_log
        WHERE status = 'success'
    """)
    loaded = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()

    # Konfigurera per kalla
    if source_type == 'podcast':
        data_dir = Path("data/podcasts/analyses-v2")
        pattern = "*.json"
    elif source_type == 'twitter':
        data_dir = Path("data/twitter/analyses")
        pattern = "*-tweet-analyses.json"
    elif source_type == 'youtube':
        data_dir = Path("data/youtube/analyses")
        pattern = "*.json"
    else:
        return []

    unsynced = []
    for f in data_dir.glob(pattern):
        if source_type == 'youtube' and f.stem.endswith('-analysis'):
            continue
        file_hash = hashlib.sha256(f.read_bytes()).hexdigest()
        path_str = str(f.absolute())
        # Ny fil eller andrad fil
        if path_str not in loaded or loaded[path_str] != file_hash:
            unsynced.append(f)

    return unsynced


def sync_unsynced_only(source_types: list[str] = None, verbose: bool = True):
    """Synka endast filer som inte redan ar laddade."""
    if source_types is None:
        source_types = ['podcast', 'twitter', 'youtube']

    engine = get_engine()
    loaders = {
        'podcast': PodcastLoader(),
        'twitter': TwitterLoader(),
        'youtube': YouTubeLoader()
    }

    results = {}

    for source_type in source_types:
        unsynced = get_unsynced_files(source_type)

        if not unsynced:
            results[source_type] = {
                "loaded": 0,
                "skipped": 0,
                "failed": 0,
                "errors": [],
                "new_recommendations": 0,
                "message": "Already up to date"
            }
            continue

        loader = loaders[source_type]
        result = {
            "loaded": 0,
            "skipped": 0,
            "failed": 0,
            "errors": [],
            "new_recommendations": 0
        }

        if verbose:
            print(f"\nSynkar {source_type}: {len(unsynced)} nya/andrade filer...")

        for i, json_path in enumerate(unsynced, 1):
            try:
                with get_session(engine) as session:
                    load_result = loader.load(json_path, session)

                    if load_result.status == "success":
                        result["loaded"] += 1
                        result["new_recommendations"] += load_result.recommendations_count
                    elif load_result.status == "skipped":
                        result["skipped"] += 1
                    else:
                        result["failed"] += 1
                        result["errors"].append((json_path.name, load_result.error))

                    if verbose and i % 50 == 0:
                        print(f"  [{i}/{len(unsynced)}] Progress...")

            except Exception as e:
                result["failed"] += 1
                result["errors"].append((json_path.name, str(e)))

        results[source_type] = result

    return results
```

## Felhantering

### Database Locked

Om databasen ar last (t.ex. av en annan process):

```python
import time
from sqlite3 import OperationalError

def sync_with_retry(loader, json_path, session, max_retries=3):
    """Ladda fil med retry vid database locked."""
    for attempt in range(max_retries):
        try:
            return loader.load(json_path, session)
        except OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1, 2, 4 sekunder
                print(f"  Database locked, vantar {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
```

### Rollback Strategy

Varje fil processas i en separat session:

```python
for json_path in files:
    with get_session(engine) as session:
        # Om nagot gar fel har, rollbackas automatiskt
        # Andra filer paverkas inte
        result = loader.load(json_path, session)
```

## Performance Tips

1. **Batch-storlek**: En fil per transaktion ar sakrast men lite langsammare
2. **Progress**: Visa progress var 50:e fil for att inte oversvamma output
3. **Skipping**: Loaders hoppar automatiskt over redan laddade filer
4. **Memory**: Filer laddas en i taget, inget behov av stor RAM

## Manuell Körning

For att kora sync manuellt via CLI:

```bash
# Ladda alla podcast-analyser
podstock db load --type podcast --data-dir data/podcasts/analyses-v2

# Ladda en specifik fil
podstock db load --type podcast --file data/podcasts/analyses-v2/episode.json

# Ladda Twitter
podstock db load --type twitter

# Ladda YouTube (observera: default dir ar fel i CLI, anvand --data-dir)
podstock db load --type youtube --data-dir data/youtube/analyses
```
