---
name: podcast-normalize
description: Validera och normalisera podcast-data. Anvand nar anvandaren fragar "normalisera podcasts", "fixa podcast-namn", "validera analyser", "podcast duplicates", eller vill kolla datakvalitet. Visar diskrepanser mellan analysfiler och podcasts.json, och kan fixa source-filer. (project)
---

# Podcast Normalize Skill

Validera podcast-analysfiler mot podcasts.json-registret och normalisera inkonsekvent data.

## Quick Start

1. **Visa status** - Identifiera diskrepanser (kor FORST)
2. Om inga problem: Visa "All data ar normaliserad!"
3. Om diskrepanser: Visa rapport och fraga anvandaren
4. Vid godkannande: Fixa source-filer
5. Regenerera dashboard

## Step 1: Check Normalization Status (Kor ALLTID forst)

```python
from pathlib import Path
import json
from collections import defaultdict

# Kopiera KNOWN_NAME_ALIASES fran exporters.py
# (eller importera: from podstock.dashboard.exporters import KNOWN_NAME_ALIASES)
KNOWN_NAME_ALIASES = {
    "kort & lang": "kortochlang",
    "kort och lang": "kortochlang",
    "analyspodden": "kortochlang",
    "analyspodden fran dagens industri": "kortochlang",
    "fill or kill": "fillorkill",
    "fil or kill": "fillorkill",
    "market makers": "marketmakers",
    "ig borssnack": "igborssnack",
    "bull & bjorn": "bullochbjorn",
    # ... se exporters.py for komplett lista
}

def get_normalization_status():
    """Identifiera inkonsekvent podcast-data."""

    # Ladda registry
    registry_path = Path("data/podcasts.json")
    registry = {}
    canonical_names = {}
    if registry_path.exists():
        with open(registry_path, encoding="utf-8") as f:
            data = json.load(f)
            for p in data.get("podcasts", []):
                registry[p["id"]] = p
                canonical_names[p["id"]] = p["name"]

    analyses_dir = Path("data/podcasts/analyses")

    if not analyses_dir.exists():
        return {"error": "Analyses directory not found"}

    # Samla statistik
    stats = {
        "total_files": 0,
        "matched_by_id": 0,
        "matched_by_name": 0,
        "unmatched": 0,
        "name_variations": defaultdict(lambda: defaultdict(list)),
        "unknown_podcasts": defaultdict(list),
    }

    for f in sorted(analyses_dir.glob("*.json")):
        stats["total_files"] += 1

        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
        except (json.JSONDecodeError, IOError):
            continue

        episode_id = data.get("episode_id", f.stem)
        podcast_name = data.get("podcast_name", "")

        # Extract podcast_id (ta allt fore YYYY-MM-DD)
        parts = episode_id.split("-")
        extracted_id = parts[0]
        for i, part in enumerate(parts):
            if len(part) == 4 and part.isdigit() and 1900 <= int(part) <= 2100:
                extracted_id = "-".join(parts[:i])
                break

        # Kolla match
        if extracted_id in registry:
            stats["matched_by_id"] += 1
            canonical_name = canonical_names[extracted_id]
            if podcast_name and podcast_name != canonical_name:
                stats["name_variations"][extracted_id][podcast_name].append(f.name)
        elif podcast_name.lower().strip() in KNOWN_NAME_ALIASES:
            stats["matched_by_name"] += 1
            canonical_id = KNOWN_NAME_ALIASES[podcast_name.lower().strip()]
            if canonical_id in canonical_names:
                canonical_name = canonical_names[canonical_id]
                if podcast_name != canonical_name:
                    stats["name_variations"][canonical_id][podcast_name].append(f.name)
        else:
            stats["unmatched"] += 1
            stats["unknown_podcasts"][extracted_id].append({
                "file": f.name,
                "name": podcast_name
            })

    return stats

# Kor och visa status
status = get_normalization_status()
if 'error' in status:
    print(f"ERROR: {status['error']}")
else:
    print("=" * 60)
    print("PODCAST NORMALIZATION STATUS")
    print("=" * 60)
    print(f"\nTotalt filer: {status['total_files']}")
    print(f"Matchade (ID): {status['matched_by_id']}")
    print(f"Matchade (namn): {status['matched_by_name']}")
    print(f"Omatchade: {status['unmatched']}")

    total_variations = sum(
        sum(len(files) for files in variations.values())
        for variations in status['name_variations'].values()
    )

    if status['name_variations']:
        print(f"\n{'=' * 60}")
        print(f"NAMN-VARIATIONER ({total_variations} filer)")
        print("=" * 60)
        for pid, variations in sorted(status['name_variations'].items()):
            canonical = registry.get(pid, {}).get("name", pid)
            print(f"\n[{pid}] Kanoniskt: '{canonical}'")
            for name, files in sorted(variations.items(), key=lambda x: -len(x[1])):
                print(f"  - '{name}' ({len(files)} filer)")

    if status['unknown_podcasts']:
        print(f"\n{'=' * 60}")
        print("OKANDA PODCASTS (lagg till i podcasts.json)")
        print("=" * 60)
        for pid, items in sorted(status['unknown_podcasts'].items(), key=lambda x: -len(x[1])):
            names = set(item['name'] for item in items)
            print(f"\n  [{pid}] {len(items)} filer")
            print(f"     Namn: {', '.join(names)}")

    print("\n" + "=" * 60)
    if total_variations == 0 and not status['unknown_podcasts']:
        print("ALL DATA AR NORMALISERAD!")
    else:
        total_issues = total_variations + len(status['unknown_podcasts'])
        print(f"TOTALT: {total_issues} problem att aga")
    print("=" * 60)
```

## Step 2: User Selection

Om det finns filer att fixa, fraga anvandaren med AskUserQuestion:

```
Jag hittade {N} filer med inkonsekvent podcast_name.

Exempel:
- 68 filer har "Kort och Lang" (ska vara "Kort & Lang - analyspodden fran Di")
- 23 filer har "Fill och Kill" (ska vara "Fill or Kill")

Vill du:
1. Fixa alla filer automatiskt (uppdatera podcast_name) - Recommended
2. Visa detaljerad rapport (inga andringar)
3. Fixa specifik podcast (ange ID)
4. Avbryt
```

## Step 3: Execute Fix

**KRITISKT: Fraga ALLTID anvandaren innan source-filer andras!**

```python
def fix_podcast_names(podcast_id: str | None = None, dry_run: bool = True):
    """Uppdatera podcast_name i analysfiler till kanoniskt namn.

    Args:
        podcast_id: Om angivet, fixa endast denna podcast
        dry_run: Om True, visa vad som skulle andras utan att andra
    """
    # Ladda registry
    registry_path = Path("data/podcasts.json")
    with open(registry_path, encoding="utf-8") as f:
        data = json.load(f)
        registry = {p["id"]: p for p in data.get("podcasts", [])}

    analyses_dir = Path("data/podcasts/analyses")

    fixed_count = 0
    skipped_count = 0

    for f in sorted(analyses_dir.glob("*.json")):
        try:
            with open(f, encoding="utf-8") as fp:
                file_data = json.load(fp)
        except (json.JSONDecodeError, IOError):
            continue

        episode_id = file_data.get("episode_id", f.stem)
        current_name = file_data.get("podcast_name", "")

        # Extract podcast_id
        parts = episode_id.split("-")
        extracted_id = parts[0]
        for i, part in enumerate(parts):
            if len(part) == 4 and part.isdigit() and 1900 <= int(part) <= 2100:
                extracted_id = "-".join(parts[:i])
                break

        # Skip om vi filtrerar pa specifik podcast
        if podcast_id and extracted_id != podcast_id:
            continue

        # Hitta kanoniskt namn
        canonical_name = None
        if extracted_id in registry:
            canonical_name = registry[extracted_id]["name"]
        elif current_name.lower().strip() in KNOWN_NAME_ALIASES:
            canonical_id = KNOWN_NAME_ALIASES[current_name.lower().strip()]
            if canonical_id in registry:
                canonical_name = registry[canonical_id]["name"]

        if not canonical_name:
            skipped_count += 1
            continue

        if current_name != canonical_name:
            if dry_run:
                print(f"[DRY RUN] {f.name}")
                print(f"         '{current_name}' -> '{canonical_name}'")
            else:
                file_data["podcast_name"] = canonical_name
                with open(f, "w", encoding="utf-8") as fp:
                    json.dump(file_data, fp, ensure_ascii=False, indent=2)
                print(f"[FIXED] {f.name}")
            fixed_count += 1

    print(f"\n{'=' * 60}")
    if dry_run:
        print(f"DRY RUN: {fixed_count} filer skulle andras")
    else:
        print(f"KLART: {fixed_count} filer andrade")
    print(f"Skippade: {skipped_count} (okanda podcasts)")
    print("=" * 60)

# Exempel: Dry run for alla
fix_podcast_names(dry_run=True)

# Exempel: Fix specifik podcast
# fix_podcast_names(podcast_id="kortochlang", dry_run=False)

# Exempel: Fix alla (efter godkannande!)
# fix_podcast_names(dry_run=False)
```

## Step 4: Regenerate Dashboard

Efter fix, regenerera dashboard:

```bash
# Om podstock CLI finns
podstock dashboard generate

# Eller direkt via Python
python -c "
from pathlib import Path
from podstock.dashboard.generator import DashboardGenerator

gen = DashboardGenerator(Path('data'))
gen.generate()
print('Dashboard regenerated!')
"
```

## Step 5: Completion Summary

```
============================================================
NORMALISERING KLAR
============================================================

Andrade: 156 filer
  - kortochlang: 89 filer ("Analyspodden" -> "Kort & Lang...")
  - fillorkill: 23 filer ("Fill och Kill" -> "Fill or Kill")
  - marketmakers: 44 filer ("Market Makers" -> "Market Makers")

Skippade: 12 filer (okanda podcasts)

Dashboard regenererad: data/dashboard/index.html

Tips: Oppna dashboard och verifiera att dropdown visar ratt namn!
============================================================
```

## Trigger Phrases

- "normalisera podcasts"
- "fixa podcast-namn"
- "validera analyser"
- "podcast duplicates"
- "kolla datakvalitet"
- "normalize podcast data"

## Registry File

Kanoniska podcast-namn definieras i:

```
data/podcasts.json
```

Struktur:
```json
{
  "podcasts": [
    {
      "id": "kortochlang",
      "name": "Kort & Lang - analyspodden fran Di",
      "rss_url": null,
      "hosts": [],
      "description": "..."
    }
  ]
}
```

## Adding New Podcasts

Om en podcast saknas i registry, lagg till den manuellt:

```python
import json
from pathlib import Path

registry_path = Path("data/podcasts.json")
with open(registry_path, encoding="utf-8") as f:
    data = json.load(f)

data["podcasts"].append({
    "id": "new-podcast-id",
    "name": "New Podcast Name",
    "rss_url": None,
    "hosts": [],
    "description": "Description here",
    "language": "sv",
    "website": None,
    "twitter": None,
    "added_at": "2024-12-29T00:00:00Z",
    "active": True
})

with open(registry_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

## Updating Name Aliases

Om nya namnvariationer upptacks, lagg till dem i:

```
src/podstock/dashboard/exporters.py
```

Under `KNOWN_NAME_ALIASES` konstanten.

## Error Handling

| Fel | Losning |
|-----|---------|
| `Registry not found` | Skapa data/podcasts.json |
| `Analyses dir not found` | Kor podcast-download forst |
| `Invalid JSON` | Logga fel, hoppa over fil |
| `Unknown podcast` | Lagg till i podcasts.json |
