# Whisper Method (RSS + Local Transcription)

Download audio via RSS feed and transcribe locally using mlx-whisper.

## Prerequisites

- Podcast must have RSS URL configured in `data/podcasts.json`
- mlx-whisper installed: `pip install mlx-whisper`
- Sufficient disk space for audio files (~50-150 MB per episode)
- Apple Silicon Mac (M1/M2/M3/M4) for optimal performance

## Key Functions

```python
from podstock.rss.parser import (
    get_all_episodes,      # Fetch all episodes from RSS
    get_latest_episodes,   # Fetch N latest episodes
    fetch_feed,            # Raw feed access
    validate_rss_url,      # Check if URL is valid RSS
)
from podstock.rss.downloader import (
    download_episode,      # Download audio with progress
    verify_download,       # Verify downloaded file
)
from podstock.transcribe.whisper import (
    transcribe,            # Transcribe audio file
    save_transcript,       # Save with metadata header
    estimate_duration,     # Estimate audio length
    get_available_models,  # List available models
)
from podstock.core.state import State
from podstock.core.models import Episode
```

## Complete Workflow

```python
from pathlib import Path
from podstock.rss.parser import get_all_episodes
from podstock.rss.downloader import download_episode
from podstock.transcribe.whisper import transcribe, save_transcript, estimate_duration
from podstock.core.state import State
from datetime import datetime
import json

# Load config
podcasts_data = json.loads(Path('data/podcasts.json').read_text())
state = State(Path('data/state.json'))

# Find podcast with RSS
podcast = next(p for p in podcasts_data['podcasts'] if p['id'] == 'borspodden')
rss_url = podcast['rss_url']
podcast_id = podcast['id']

# 1. Get episodes from RSS
episodes = get_all_episodes(rss_url, podcast_id)

# Filter to 2025+ and not transcribed
cutoff = datetime(2025, 1, 1)
to_sync = [ep for ep in episodes if ep.published_at >= cutoff and not state.is_transcribed(ep.id)]

print(f"Found {len(to_sync)} episodes to sync")

# 2. Process each episode
for i, episode in enumerate(to_sync):
    print(f"\n[{i+1}/{len(to_sync)}] {episode.id}")
    print(f"  Title: {episode.title[:50]}...")

    # Download audio
    audio_dir = Path(f'data/audio/{podcast_id}')
    print(f"  [Whisper] Downloading audio...")

    audio_path = download_episode(
        episode,
        audio_dir,
        show_progress=True
    )

    # Update state
    state.mark_downloaded(episode.id, audio_path)

    # Estimate duration
    duration = estimate_duration(audio_path)
    if duration:
        print(f"  [Whisper] Audio length: {duration // 60} minutes")

    # Transcribe
    print(f"  [Whisper] Transcribing with large-v3...")

    def progress(msg):
        print(f"    {msg}")

    text = transcribe(
        audio_path,
        model="large-v3",
        language="sv",
        progress_callback=progress
    )

    word_count = len(text.split())
    print(f"  [Whisper] Done: {word_count:,} words")

    # Save transcript
    transcript_dir = Path('data/transcripts')
    transcript_path = save_transcript(
        episode.id,
        text,
        transcript_dir,
        podcast_id,
        metadata={
            "source": "whisper",
            "model": "large-v3",
            "original_title": episode.title,
            "pub_date": episode.published_at.strftime("%Y-%m-%d"),
        }
    )

    # Update state
    state.mark_transcribed(
        episode.id,
        transcript_path,
        source="whisper",
        has_timestamps=False  # Whisper output doesn't include timestamps
    )

    print(f"  Saved: {transcript_path}")
```

## Episode Object (from RSS)

```python
@dataclass
class Episode:
    id: str                    # "borspodden-2025-02-19-a1b2"
    podcast_id: str            # "borspodden"
    title: str                 # "Avsnitt 612 - Rapportfloden"
    published_at: datetime     # 2025-02-19 12:00:00
    audio_url: str            # "https://traffic.libsyn.com/..."
    duration_seconds: int     # 3600
    description: str          # Episode description
    guid: str                 # RSS GUID
```

## Duration Estimates

Transcription time depends on:
- Audio length
- Model size (large-v3 is most accurate but slowest)
- Hardware (Apple Silicon M1/M2/M3/M4)

| Audio Length | Approx. Time (M1) | Approx. Time (M3 Pro) |
|--------------|-------------------|------------------------|
| 30 min | ~5-7 min | ~3-4 min |
| 1 hour | ~10-15 min | ~6-8 min |
| 90 min | ~15-20 min | ~10-12 min |

## Whisper Models

Available models (smallest to largest):

| Model | Quality | Speed | VRAM |
|-------|---------|-------|------|
| tiny | Low | Fastest | ~1 GB |
| base | Low-Med | Fast | ~1 GB |
| small | Medium | Medium | ~2 GB |
| medium | Good | Slow | ~5 GB |
| large | Best | Slowest | ~10 GB |
| large-v2 | Best | Slowest | ~10 GB |
| large-v3 | Best (default) | Slowest | ~10 GB |

For Swedish podcasts, `large-v3` is recommended for accuracy.

## Output Format

Transcripts are saved without timestamps (Whisper basic mode):

```
============================================================
Episode: borspodden-2025-02-19-a1b2
Podcast: borspodden
source: whisper
model: large-v3
original_title: Avsnitt 612 - Rapportfloden fortsatter
pub_date: 2025-02-19
============================================================

Välkomna till Börspodden. Idag ska vi prata om rapportsäsongen
som nu är i full gång. Vi har sett en hel del överraskningar...
```

## Error Handling

| Error | Solution |
|-------|----------|
| `RSS feed has no entries` | Check RSS URL, may be rate limited |
| `Failed to download after 3 attempts` | Network issue, try again later |
| `Audio file not found` | Download failed silently, check audio_path |
| `mlx-whisper not installed` | Run `pip install mlx-whisper` |
| `MLX transcription error` | OOM - try smaller model or restart |
| `Transcription returned empty` | Audio may be silent or corrupt |

## Cleanup (Optional)

After successful transcription, audio files can be deleted to save space:

```python
# Only delete if transcript exists and is verified
if state.is_transcribed(episode.id):
    audio_path = state.get_audio_path(episode.id)
    if audio_path and audio_path.exists():
        audio_path.unlink()
        print(f"Deleted audio: {audio_path}")
```

## Podcasts with RSS

From `data/podcasts.json`:

| Podcast | RSS URL |
|---------|---------|
| borspodden | https://borspodden.libsyn.com/rss |
| borsmagasinet | https://feeds.acast.com/public/shows/borsmagasinet |
| marketmakers | https://feeds.acast.com/public/shows/marketmakers |
| fillorkill | https://fillorkill.libsyn.com/rss |
| gotttjot | https://feeds.acast.com/public/shows/nantingomaktier |
