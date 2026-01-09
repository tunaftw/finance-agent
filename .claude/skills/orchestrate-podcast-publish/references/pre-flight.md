# Pre-flight Check

Validera att miljön är redo innan orchestration-körning startar.

## Checklista

### 1. Apple Podcasts Database

```bash
APPLE_DB="$HOME/Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Documents/MTLibrary.sqlite"

if [ -f "$APPLE_DB" ]; then
    echo "✓ Apple Podcasts DB finns"

    # Kolla att den inte är för gammal
    MODIFIED=$(stat -f %m "$APPLE_DB")
    NOW=$(date +%s)
    AGE_DAYS=$(( (NOW - MODIFIED) / 86400 ))

    if [ $AGE_DAYS -gt 7 ]; then
        echo "⚠ Apple Podcasts DB är $AGE_DAYS dagar gammal - öppna appen för att synka"
    fi
else
    echo "✗ Apple Podcasts DB saknas"
    echo "  → Installera och öppna Apple Podcasts app"
    exit 1
fi
```

### 2. Podcast Mapping

```bash
if [ -f "data/podcast_mapping.json" ]; then
    echo "✓ Podcast mapping finns"

    # Validera JSON
    python3 -c "import json; json.load(open('data/podcast_mapping.json'))" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "✗ podcast_mapping.json är invalid JSON"
        exit 1
    fi
else
    echo "✗ data/podcast_mapping.json saknas"
    exit 1
fi
```

### 3. PodStock Database

```bash
if [ -f "data/podstock.db" ]; then
    echo "✓ Database finns"

    # Kolla att den är läsbar
    sqlite3 data/podstock.db "SELECT COUNT(*) FROM sources;" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "✗ Database är korrupt eller låst"
        exit 1
    fi
else
    echo "⚠ Database saknas - initierar..."
    podstock db init
fi
```

### 4. OpenCode/GLM-4.7 Tillgänglighet

```bash
# Kolla att batch runner finns
BATCH_SCRIPT="/Users/pontus/Developer/podcast-transcriber/scripts/batch_runner.py"

if [ -f "$BATCH_SCRIPT" ]; then
    echo "✓ Batch runner finns"
else
    echo "✗ Batch runner saknas: $BATCH_SCRIPT"
    exit 1
fi

# Kolla att OpenCode är installerat
which opencode >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ OpenCode installerat"
else
    echo "⚠ OpenCode inte i PATH - batch-analys kan misslyckas"
fi
```

### 5. Git Working Tree

```bash
if git diff --quiet && git diff --cached --quiet; then
    echo "✓ Git working tree är ren"
else
    echo "⚠ Git har uncommitted changes:"
    git status --short

    # Fråga användaren
    read -p "Fortsätta ändå? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Avbryter - committa ändringar först"
        exit 1
    fi
fi
```

### 6. Disk Space

```bash
# Kolla att det finns tillräckligt med utrymme (minst 1GB)
AVAILABLE=$(df -g . | tail -1 | awk '{print $4}')

if [ "$AVAILABLE" -lt 1 ]; then
    echo "✗ Mindre än 1GB ledigt diskutrymme"
    exit 1
else
    echo "✓ Diskutrymme OK (${AVAILABLE}GB ledigt)"
fi
```

## Komplett Pre-flight Script

```python
import subprocess
import sys
from pathlib import Path

def pre_flight_check():
    """Kör alla pre-flight checks. Returnerar True om allt OK."""

    errors = []
    warnings = []

    # 1. Apple Podcasts DB
    apple_db = Path.home() / "Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Documents/MTLibrary.sqlite"
    if not apple_db.exists():
        errors.append("Apple Podcasts DB saknas")

    # 2. Podcast mapping
    mapping = Path("data/podcast_mapping.json")
    if not mapping.exists():
        errors.append("data/podcast_mapping.json saknas")

    # 3. Database
    db = Path("data/podstock.db")
    if not db.exists():
        warnings.append("Database saknas - kommer initieras")

    # 4. Git status
    result = subprocess.run(["git", "diff", "--quiet"], capture_output=True)
    if result.returncode != 0:
        warnings.append("Git har uncommitted changes")

    # Rapportera
    if errors:
        print("PRE-FLIGHT FAILED")
        for e in errors:
            print(f"  ✗ {e}")
        return False

    if warnings:
        print("PRE-FLIGHT WARNINGS")
        for w in warnings:
            print(f"  ⚠ {w}")

    print("✓ Pre-flight check passed")
    return True

if __name__ == "__main__":
    if not pre_flight_check():
        sys.exit(1)
```

## Hantering av Fel

| Check | Kritiskt? | Åtgärd |
|-------|-----------|--------|
| Apple Podcasts DB saknas | Ja | STOPP - användaren måste installera appen |
| Podcast mapping saknas | Ja | STOPP - filen behövs |
| Database saknas | Nej | Init:a automatiskt |
| Git dirty | Nej | Fråga användaren |
| OpenCode saknas | Nej | Varning - batch kan misslyckas |
| Disk full | Ja | STOPP |
