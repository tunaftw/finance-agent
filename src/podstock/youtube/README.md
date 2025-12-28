# YouTube Module

Samlar och hanterar YouTube-kanaler och transkript.

## Syfte

- Hantera YouTube-kanaler som datakällor
- Extrahera transkript från videor
- Förbereda data för analys (crypto, stocks, etc.)

## Användning

### Lägg till kanal

```python
from podstock.youtube.channel_manager import YouTubeChannelManager

manager = YouTubeChannelManager(data_dir=Path("data"))

# Lägg till kanal
manager.add_channel(
    id="technical-roundup",
    handle="@TechnicalRoundup",
    name="Technical Roundup",
    category="crypto",
)
```

### Extrahera transkript

```python
from podstock.youtube.extractor import YouTubeExtractor

extractor = YouTubeExtractor()

# Extrahera från video
transcript = extractor.extract_transcript(
    video_id="dQw4w9WgXcQ",
    channel_id="technical-roundup",
)

# Spara
extractor.save_transcript(transcript, Path("data/youtube/transcripts/"))
```

## Datamodeller

### YouTubeChannel

```python
class YouTubeChannel(BaseModel):
    id: str                    # Vår slug: "technical-roundup"
    channel_id: str | None     # YouTube's UC... ID
    handle: str                # @TechnicalRoundup
    name: str
    description: str | None
    category: str              # "crypto", "finance", "tech"
    language: str              # default: "en"
    subscriber_count: int | None
    active: bool
```

### YouTubeVideo

```python
class YouTubeVideo(BaseModel):
    id: str                    # YouTube video ID (11 chars)
    channel_id: str            # Vår kanal-slug
    title: str
    published_at: datetime
    duration_seconds: int
    view_count: int | None

    has_transcript: bool
    transcript_language: str | None
    transcript_type: Literal["auto", "manual", "none"]

    mentioned_cryptos: list[str]  # Extraherade krypto-omnämnanden
```

### VideoTranscript

```python
class VideoTranscript(BaseModel):
    video_id: str
    channel_id: str
    language: str

    text: str                  # Full transkript-text
    segments: list[TranscriptSegment]
    word_count: int
    duration_seconds: int

    extracted_at: datetime
```

### TranscriptSegment

```python
class TranscriptSegment(BaseModel):
    start: float    # Sekunder
    end: float
    text: str
```

## Filer

| Fil | Beskrivning |
|-----|-------------|
| `models.py` | YouTubeChannel, YouTubeVideo, VideoTranscript |
| `channel_manager.py` | CRUD för YouTube-kanaler |
| `extractor.py` | Transkript-extraktion från YouTube |
| `storage.py` | Lagring av videor och transkript |
| `state.py` | Collection state per kanal |
| `exceptions.py` | Modul-specifika exceptions |

## CLI-kommandon

```bash
# Lägg till kanal
podstock youtube add technical-roundup --handle @TechnicalRoundup --category crypto

# Lista kanaler
podstock youtube list

# Samla videor
podstock youtube collect technical-roundup --since 2024-01-01

# Extrahera transkript
podstock youtube transcribe technical-roundup
```

## Lagring

- `data/youtube/raw/{channel_id}/` - Rådata (metadata, transcripts)
- `data/youtube/analyses/` - LLM-analyser (crypto sentiment, etc.)
- `data/youtube/sources.json` - Konfigurerade kanaler
- `data/youtube/state.json` - Collection state
- `data/youtube/index/` - Sökindex

## Konfiguration

Kanaler konfigureras i `data/youtube/sources.json`:

```json
{
  "version": 1,
  "channels": [
    {
      "id": "technical-roundup",
      "handle": "@TechnicalRoundup",
      "name": "Technical Roundup",
      "category": "crypto",
      "language": "en",
      "active": true
    }
  ]
}
```

## Integration med Crypto-modul

Transkript från YouTube används av `crypto/` för sentiment-analys:

```python
from podstock.crypto.analyzer import CryptoAnalyzer

# Ladda transkript
transcript_path = Path("data/youtube/transcripts/technical-roundup/dQw4w9WgXcQ.txt")

# Analysera med crypto-modul
analysis = analyzer.analyze_transcript(
    transcript_path=transcript_path,
    source_type="youtube",
    channel_name="Technical Roundup",
)
```

## Se även

- `docs/ANALYSIS-GUIDE.md` - Arkitekturdokumentation
- `crypto/` - Crypto sentiment-analys
