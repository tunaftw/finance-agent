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

## Workflow: Download Missing Transcripts

For transcripts not yet cached, use the FetchTranscript helper script:

```bash
# Download using OUR podcast ID (recommended)
python scripts/download_apple_transcripts.py --podcast marketmakers --max 10
python scripts/download_apple_transcripts.py --podcast fillorkill --max 10

# Or using Apple's podcast name (also works)
python scripts/download_apple_transcripts.py --podcast "Market Makers" --max 10

# Download all available transcripts
python scripts/download_apple_transcripts.py --max 50
```

**VIKTIGT:** Scriptet stodjer BADE:
- Vara podcast-ID:n (t.ex. `marketmakers`, `fillorkill`, `borspodden`)
- Apple-namn (t.ex. `Market Makers`, `Fill or Kill`, `Börspodden`)

Scriptet oversatter automatiskt via `data/podcast_mapping.json`.

The script:
1. Resolves podcast ID to Apple name (if needed) using `podcast_mapping.json`
2. Queries Apple Podcasts DB for episodes with transcripts
3. Checks which are not yet in local TTML cache
4. Uses FetchTranscript tool to download TTML files
5. Saves to the cache directory for later extraction

After downloading, **you must extract TTML to text files** - see orchestrate-podcast-publish skill for extraction code.

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

## Checking Transcript Availability

```python
from podstock.transcribe.apple import get_transcript_stats

stats = get_transcript_stats()
print(f"Total in database: {stats['total_in_database']}")
print(f"Cached locally: {stats['total_cached']}")

for podcast_name, counts in stats['by_podcast'].items():
    print(f"  {podcast_name}: {counts['cached']}/{counts['total']} cached")
```
