---
name: podcast-download
description: Sync podcast transcripts. Use when user asks "vilka podcasts har kommit som inte ar synkade", wants to check unsynced episodes, or download missing transcripts. Identifies episodes from 2025 onwards lacking transcripts and syncs using Apple Podcasts (preferred) or Whisper (fallback).
---

# Podcast Download Skill

Sync podcast transcripts for unsynced episodes from 2025 onwards.

## Quick Start

1. Check sync status for all configured podcasts
2. User selects: all podcasts or specific ones
3. Execute sync using appropriate method per episode
4. Report summary of what was synced and where

## Workflow

### Step 1: Check Sync Status

Identify unsynced episodes (published 2025+ without transcript).

**Important**: Use date-based matching since episode IDs may differ between sources (RSS, Apple, Whisper use different title hashes).

```python
import json
from pathlib import Path
from datetime import datetime
from podstock.rss.parser import get_all_episodes
from podstock.core.models import Podcast

# Helper: Check if transcript exists by date (ignores hash differences)
def transcript_exists(podcast_id: str, pub_date: datetime) -> bool:
    date_str = pub_date.strftime('%Y-%m-%d')
    pattern = f'{podcast_id}-{date_str}-*.txt'
    transcript_dir = Path(f'data/podcasts/raw/{podcast_id}/transcripts')
    if not transcript_dir.exists():
        return False
    return len(list(transcript_dir.glob(pattern))) > 0

# Load configurations
podcasts_data = json.loads(Path('data/podcasts.json').read_text())
podcasts = [Podcast(**p) for p in podcasts_data['podcasts'] if p.get('active', True)]

cutoff = datetime(2025, 1, 1)
unsynced = {}  # {podcast_id: [episodes]}

# Check RSS-enabled podcasts
for podcast in podcasts:
    if podcast.rss_url:
        try:
            episodes = get_all_episodes(podcast.rss_url, podcast.id)
            for ep in episodes:
                if ep.published_at >= cutoff and not transcript_exists(podcast.id, ep.published_at):
                    unsynced.setdefault(podcast.id, []).append({
                        'id': ep.id,
                        'title': ep.title,
                        'date': ep.published_at,
                        'source': 'rss'
                    })
        except Exception as e:
            print(f"Warning: Could not fetch RSS for {podcast.name}: {e}")

# Check Apple Podcasts database for Apple-only podcasts
from podstock.transcribe.apple import list_available_transcripts, match_to_podcast
try:
    apple_transcripts = list_available_transcripts(podcasts)
    for t in apple_transcripts:
        if t.pub_date >= cutoff:
            matched_podcast = match_to_podcast(t.podcast_name, podcasts)
            if matched_podcast and not transcript_exists(matched_podcast.id, t.pub_date):
                from podstock.transcribe.apple import _generate_episode_id
                ep_id = _generate_episode_id(matched_podcast.id, t.pub_date, t.episode_title)
                unsynced.setdefault(matched_podcast.id, []).append({
                    'id': ep_id,
                    'title': t.episode_title,
                    'date': t.pub_date,
                    'source': 'apple',
                    'is_cached': t.is_cached,
                    'transcript': t
                })
except Exception as e:
    print(f"Warning: Could not read Apple Podcasts database: {e}")
```

### Step 2: Display Unsynced Summary

Print status report:

```
================================================================================
PODCAST SYNC STATUS (2025+)
================================================================================

BORSPODDEN (5 osynkade)
  Metod: Apple Podcasts (3 cachade, 2 ej cachade)
  - 2025-02-19: "Avsnitt 612 - Rapportfloden..."
  - 2025-02-12: "Avsnitt 611 - Analyssnack..."
  ...

MARKET MAKERS (3 osynkade)
  Metod: Whisper (ingen Apple-transcript tillganglig)
  - 2025-01-15: "EP 234 - Tech-rotation..."
  ...

SPARPODDEN (2 osynkade)
  Metod: Apple Podcasts (2 cachade)
  - 2025-01-20: "Avsnitt 89 - Fondval..."
  ...

--------------------------------------------------------------------------------
SAMMANFATTNING: 10 avsnitt behover synkas
  - Apple Podcasts: 7 avsnitt (5 cachade, 2 behover FetchTranscript)
  - Whisper: 3 avsnitt
--------------------------------------------------------------------------------
```

### Step 3: User Selection

Ask user (use AskUserQuestion tool):

```
Vad vill du gora?
1. Synka alla osynkade avsnitt (10 st)
2. Synka specifika podcasts (ange namn)
3. Avbryt
```

### Step 4: Execute Sync

**Method priority:**
1. Apple cached transcript -> immediate extraction
2. Apple downloadable -> FetchTranscript tool
3. RSS + Whisper -> download audio, transcribe locally

**For Apple method:** See [references/apple-method.md](references/apple-method.md)

**For Whisper method:** See [references/whisper-method.md](references/whisper-method.md)

**Progress output format:**

```
[1/10] borspodden-2025-02-19-a1b2
  [Apple Cached] Extraherar transcript... klart (3,542 ord)
  Sparat: data/transcripts/borspodden/borspodden-2025-02-19-a1b2.txt

[2/10] borspodden-2025-02-12-c3d4
  [Apple Download] Hamtar transcript via FetchTranscript... klart
  [Apple Download] Extraherar... klart (4,128 ord)
  Sparat: data/transcripts/borspodden/borspodden-2025-02-12-c3d4.txt

[3/10] marketmakers-2025-01-15-e5f6
  [Whisper] Laddar ner audio... 45.2 MB (1:23 kvar)
  [Whisper] Transkriberar med large-v3... 25%... 50%... 75%... klart
  [Whisper] Transcript: 8,921 ord
  Sparat: data/transcripts/marketmakers/marketmakers-2025-01-15-e5f6.txt
```

### Step 5: Completion Summary

```
================================================================================
SYNC KLAR
================================================================================

Synkade: 9/10 avsnitt
  - Apple Podcasts: 7 avsnitt
  - Whisper: 2 avsnitt

Misslyckades: 1 avsnitt
  - marketmakers-2025-01-20-g7h8: Audio download failed (404)

Transcripts sparade i:
  data/transcripts/{podcast_id}/{episode_id}.txt

State uppdaterad: data/state.json
================================================================================
```

## Method Selection

| Scenario | Method | Notes |
|----------|--------|-------|
| Apple transcript cached | Apple (immediate) | Fastest, high quality |
| Apple transcript available but not cached | Apple (FetchTranscript) | Requires tool, high quality |
| RSS available, no Apple transcript | Whisper | ~10-15 min/hour audio |
| No RSS, no Apple transcript | Cannot sync | Need to configure RSS or view in Apple Podcasts |

## Podcasts by Method

| Podcast | RSS | Primary Method |
|---------|-----|----------------|
| borspodden | Yes | Apple or Whisper |
| borsmagasinet | Yes | Apple or Whisper |
| marketmakers | Yes | Apple or Whisper |
| fillorkill | Yes | Apple or Whisper |
| gotttjot | Yes | Apple or Whisper |
| kortochlang | No | Apple only |
| sparpodden | No | Apple only |
| marknaden | No | Apple only |
| kvalitetsaktiepodden | No | Apple only |
| aktiepodden | No | Apple only |
| veckanstrade | No | Apple only |
| ettrikareliv | No | Apple only |
| avanzapodden | No | Apple only |
| smaspararpodden | No | Apple only |
| borsensfinest | No | Apple only |
| kvalitetforpengarna | No | Apple only |

## Storage Locations

- Transcripts: `data/transcripts/{podcast_id}/{episode_id}.txt`
- Audio (Whisper): `data/audio/{podcast_id}/{episode_id}.mp3`
- State: `data/state.json`

## Error Handling

| Error | Resolution |
|-------|------------|
| RSS fetch failed | Log warning, skip podcast, continue with others |
| Apple DB not found | Fall back to RSS-only podcasts |
| Audio download 404 | Log error, skip episode, continue |
| Whisper OOM/timeout | Log error, keep audio for manual retry |
| FetchTranscript failed | Fall back to Whisper if RSS available |

## Sync Definition

An episode is considered "synced" when:
- `state.is_transcribed(episode_id)` returns `True`
- A transcript file exists at expected path
