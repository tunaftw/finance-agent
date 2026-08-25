# Apple Podcasts Method

Extract transcripts from Apple Podcasts app cache or download via FetchTranscript.

## Prerequisites

- macOS with Apple Podcasts app installed
- Episodes must have transcripts enabled by the podcast publisher
- For cached transcripts: User must have viewed the transcript in Apple Podcasts app
- For downloading: FetchTranscript binary at `tools/apple-transcripts/FetchTranscript`

## FetchTranscript Setup

The FetchTranscript binary enables downloading TTML transcripts directly from Apple servers.

**Location:** `tools/apple-transcripts/FetchTranscript`

**Source:** https://github.com/dado3212/apple-podcast-transcript-downloader

**Build instructions:**
```bash
cd tools/apple-transcripts
git clone https://github.com/dado3212/apple-podcast-transcript-downloader .
swift build -c release
cp .build/release/FetchTranscript .
```

**IMPORTANT:** Always run scripts from project root, not from subdirectories.

## Key Functions

```python
from podstock.transcribe.apple import (
    list_available_transcripts,  # Query Apple DB for available transcripts
    match_to_podcast,            # Match Apple name to configured podcast
    get_cached_transcripts_for_podcast,  # Get cached transcripts for one podcast
    extract_and_save,            # Extract TTML and save as .txt
    parse_ttml,                  # Parse TTML content
    find_database,               # Check if Apple DB exists
    find_ttml_cache,             # Check if TTML cache exists
)
from podstock.core.state import State
from podstock.core.models import Podcast
```

## Data Locations

- Apple Podcasts database: `~/Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Documents/MTLibrary.sqlite`
- TTML cache: `~/Library/Group Containers/243LU875E5.groups.com.apple.podcasts/Library/Cache/Assets/TTML`

## Workflow: Cached Transcripts

For transcripts already in local cache:

```python
from pathlib import Path
from podstock.transcribe.apple import (
    list_available_transcripts,
    match_to_podcast,
    extract_and_save,
)
from podstock.core.state import State
from podstock.core.models import Podcast
import json

# Load config
podcasts_data = json.loads(Path('data/podcasts.json').read_text())
podcasts = [Podcast(**p) for p in podcasts_data['podcasts']]
state = State(Path('data/state.json'))

# Get available transcripts
transcripts = list_available_transcripts(podcasts)

# Filter to cached only
cached = [t for t in transcripts if t.is_cached]

for t in cached:
    # Match to configured podcast
    podcast = match_to_podcast(t.podcast_name, podcasts)
    if not podcast:
        print(f"Skipping unmatched podcast: {t.podcast_name}")
        continue

    # Extract and save
    transcript_dir = Path('data/transcripts')
    transcript_path, episode_id = extract_and_save(
        transcript=t,
        transcript_dir=transcript_dir,
        podcast=podcast,
        with_timestamps=True
    )

    # Update state
    state.mark_transcribed(
        episode_id,
        transcript_path,
        source="apple",
        has_timestamps=True
    )

    print(f"Extracted: {episode_id}")
    print(f"  Saved to: {transcript_path}")
```

## Workflow: Download Missing Transcripts (Recommended)

Use the pure Python script with bearer token:

```bash
# 1. Ensure bearer token is valid (refresh if needed)
./scripts/refresh_apple_token.sh

# 2. Check what's missing
python3 scripts/fetch_transcript_pure_python.py --dry-run --year 2026

# 3. Download all missing transcripts
python3 scripts/fetch_transcript_pure_python.py --year 2026

# 4. Or limit downloads
python3 scripts/fetch_transcript_pure_python.py --year 2026 --max 10
```

The script:
1. Loads bearer token from `tools/apple-transcripts/bearer_token.txt`
2. Queries Apple Podcasts DB for episodes with transcripts
3. Filters to episodes missing local transcript files
4. Downloads TTML via Apple API
5. Extracts text and saves directly to `data/transcripts/{podcast_id}/`

**No extraction step needed** - transcripts are saved as ready-to-use text files,
**with speaker labels**: Apple's TTML tags every paragraph with
`ttm:agent="SPEAKER_N"`, and the script's parser (shared with
`scripts/extract_ttml.py`) preserves them as `[SPEAKER_1]`/`[SPEAKER_2]` blocks.
No audio diarization needed. Never extract with the old word-level regex
(`podcasts:unit="word"` findall) - it silently discards speaker information.

## Fresh Episodes (released today)

Episodes released the same day often have **no transcript identifier in the
local Apple DB yet** (`ZTRANSCRIPTIDENTIFIER` is NULL), so the year-based sync
won't see them. The transcript usually exists on Apple's servers anyway - fetch
it directly via the episode's store ID:

```bash
# 1. Get the store track ID
sqlite3 -readonly ~/Library/Group\ Containers/243LU875E5.groups.com.apple.podcasts/Documents/MTLibrary.sqlite \
  "SELECT ZTITLE, ZSTORETRACKID FROM ZMTEPISODE WHERE ZTITLE LIKE 'Avsnitt 595%'"

# 2. Download + extract in one step
python3 scripts/fetch_transcript_pure_python.py --store-id <ZSTORETRACKID>
```

## Manual TTML Extraction

For a TTML file you already have (Apple cache or manual download), use
`scripts/extract_ttml.py` - it preserves speaker labels and can look up
title/date from the Apple DB via the store ID in the filename:

```bash
python3 scripts/extract_ttml.py path/to/transcript_1000785814768.ttml --podcast fillorkill
```

### Legacy Script (DEPRECATED)

`download_apple_transcripts.py` exists but uses the broken FetchTranscript tool. Don't use it.

## AppleTranscript Object

```python
@dataclass
class AppleTranscript:
    episode_title: str      # "Avsnitt 612 - Rapportfloden"
    podcast_name: str       # "Borspodden"
    pub_date: datetime      # 2025-02-19 12:00:00
    transcript_id: str      # "transcript_12345.ttml"
    ttml_path: Path | None  # Path if cached, None otherwise
    is_cached: bool         # True if TTML exists locally
```

## TTML Format

Apple uses TTML (Timed Text Markup Language) with:
- `<p>` elements for paragraphs with timestamps
- `<span podcasts:unit="sentence">` for sentences
- `<span podcasts:unit="word">` for individual words

The `parse_ttml()` function extracts text with optional timestamps in `[MM:SS]` format.

## Output Format

Transcripts are saved with metadata header:

```
============================================================
Episode: borspodden-2025-02-19-a1b2
Podcast: borspodden
source: apple
original_title: Avsnitt 612 - Rapportfloden fortsatter
pub_date: 2025-02-19
has_timestamps: True
============================================================

[00:00] Välkomna till Börspodden...
[00:15] Idag ska vi prata om rapportsäsongen...
```

## Error Handling

| Error | Solution |
|-------|----------|
| `Apple Podcasts database not found` | Install/open Apple Podcasts app |
| `Transcript not cached locally` | View transcript in Apple Podcasts, or use FetchTranscript |
| `No text content found in TTML` | TTML file may be corrupted, try re-downloading |
| `Failed to parse TTML XML` | File format issue, check file manually |

## Known Issues

### Bearer Token Expiration (401 Errors)

**Symptom:**
```
401 Client Error: Unauthorized for url: https://amp-api.podcasts.apple.com/...
```

**Orsak:**
Bearer token har gått ut (giltig i 30 dagar).

**Lösning:**
```bash
./scripts/refresh_apple_token.sh
```

### FetchTranscript fork() Crash (DEPRECATED)

**Symptom:**
```
objc[...]: +[NSDateFormatter initialize] may have been in progress in another thread when fork() was called
```

**Orsak:**
FetchTranscript använder internt `fork()` (rad 14 i FetchTranscript.m) för att wrappa potentiella segfaults. På modern macOS kraschar detta eftersom Objective-C runtime redan är initierad.

**VIKTIG LÄRDOM:** Problemet är i FetchTranscript-verktyget självt, INTE i hur vi anropar det. Varken subprocess, osascript, eller att köra direkt i Terminal fungerar.

**Lösning:**
Använd INTE FetchTranscript. Istället:

1. **GetBearerToken** - Ny binär som hämtar bearer token utan fork()
2. **fetch_transcript_pure_python.py** - Ren Python som använder token för att ladda ner

```bash
# Hämta ny token
./scripts/refresh_apple_token.sh

# Ladda ner transcripts
python3 scripts/fetch_transcript_pure_python.py --year 2026
```

### Varför GetBearerToken fungerar

GetBearerToken löser fork()-problemet genom att:
1. Använda `continueWithBlock:` istället för `thenWithBlock:` för promise-hantering
2. Göra synkrona HTTP-anrop inuti callback:en
3. Anropa `_exit(0)` direkt efter att ha skrivit ut token för att undvika promise cleanup-kraschen

Se `tools/apple-transcripts/README.md` för tekniska detaljer.

## Checking Transcript Availability

```python
from podstock.transcribe.apple import get_transcript_stats

stats = get_transcript_stats()
print(f"Total in database: {stats['total_in_database']}")
print(f"Cached locally: {stats['total_cached']}")

for podcast_name, counts in stats['by_podcast'].items():
    print(f"  {podcast_name}: {counts['cached']}/{counts['total']} cached")
```
