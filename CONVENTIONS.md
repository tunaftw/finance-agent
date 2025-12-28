# PodStock – Coding Conventions

**Version:** 1.0  
**Datum:** 2024-12-21

---

## 1. Python Style

### 1.1 General
- **Python version:** 3.11+
- **Line length:** 100 characters max
- **Formatter:** ruff format
- **Linter:** ruff check
- **Type checker:** mypy (strict mode)

### 1.2 Imports
```python
# Ordning: stdlib → third-party → local
# Använd absolute imports

# ✅ Correct
from pathlib import Path
from datetime import datetime

import feedparser
from pydantic import BaseModel
from rich.console import Console

from podstock.core.models import Episode
from podstock.core.config import Config

# ❌ Wrong
from podstock.core.models import *  # No wildcard imports
import os, sys  # One import per line
```

### 1.3 Type Hints
```python
# ✅ Alla publika funktioner ska ha type hints
def download_episode(
    episode: Episode,
    dest_dir: Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Download episode audio file."""
    ...

# ✅ Använd moderna type hints (Python 3.10+)
def get_episodes(podcast_id: str) -> list[Episode]:
    ...

def find_podcast(id: str) -> Podcast | None:
    ...

# ✅ Använd TypeAlias för komplexa typer
type EpisodeId = str
type RecommendationMap = dict[EpisodeId, list[Recommendation]]
```

### 1.4 Docstrings
```python
def transcribe(
    audio_path: Path,
    model: str = "large-v3",
) -> str:
    """Transcribe audio file using mlx-whisper.
    
    Args:
        audio_path: Path to audio file (mp3, m4a, wav).
        model: Whisper model to use. Defaults to "large-v3".
    
    Returns:
        Transcribed text as string.
    
    Raises:
        TranscribeError: If transcription fails.
        FileNotFoundError: If audio file doesn't exist.
    
    Example:
        >>> text = transcribe(Path("episode.mp3"))
        >>> print(text[:100])
        "Välkomna till Börspodden..."
    """
```

### 1.5 Naming
```python
# Moduler: snake_case
# prompt_builder.py

# Klasser: PascalCase
class EpisodeDownloader:
    pass

# Funktioner: snake_case
def download_episode():
    pass

# Konstanter: SCREAMING_SNAKE_CASE
DEFAULT_WHISPER_MODEL = "large-v3"
MAX_RETRY_ATTEMPTS = 3

# Privata: prefix med underscore
def _validate_url(url: str) -> bool:
    pass
```

---

## 2. Code Organization

### 2.1 Module Structure
```python
"""Module docstring describing purpose.

This module provides...
"""

# Imports (grouped and sorted)
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from podstock.core.config import Config

# Constants
DEFAULT_TIMEOUT = 30
RETRY_DELAY = 1.0

# Logger
logger = logging.getLogger(__name__)

# Classes and functions
class MyClass:
    ...

def my_function():
    ...

# No code at module level (except constants/logger)
```

### 2.2 Class Structure
```python
class EpisodeDownloader:
    """Downloads podcast episodes."""
    
    # Class constants first
    DEFAULT_CHUNK_SIZE = 8192
    
    def __init__(self, config: Config) -> None:
        """Initialize downloader."""
        self._config = config
        self._session = self._create_session()
    
    # Public methods
    def download(self, episode: Episode) -> Path:
        """Download episode."""
        ...
    
    # Private methods after public
    def _create_session(self) -> requests.Session:
        ...
    
    # Properties at the end
    @property
    def timeout(self) -> int:
        return self._config.download_timeout
```

---

## 3. Error Handling

### 3.1 Exception Design
```python
# ✅ Specific exceptions with context
class DownloadError(PodStockError):
    """Failed to download episode."""
    
    def __init__(
        self,
        message: str,
        episode_id: str,
        url: str,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.episode_id = episode_id
        self.url = url
        self.__cause__ = cause

# ✅ Usage
try:
    response = requests.get(url)
    response.raise_for_status()
except requests.RequestException as e:
    raise DownloadError(
        f"Failed to download: {e}",
        episode_id=episode.id,
        url=url,
        cause=e,
    ) from e
```

### 3.2 Error Messages
```python
# ✅ Actionable error messages
raise ConfigError(
    f"Config file not found: {config_path}\n"
    f"Run 'podstock init' to create a default configuration."
)

# ❌ Not helpful
raise ConfigError("Config error")
```

### 3.3 Logging
```python
import logging

logger = logging.getLogger(__name__)

# ✅ Appropriate log levels
logger.debug("Processing episode %s", episode.id)
logger.info("Downloaded %s (%d MB)", episode.title, size_mb)
logger.warning("Retry %d/%d for %s", attempt, max_attempts, url)
logger.error("Failed to transcribe: %s", error)

# ✅ Use lazy formatting
logger.debug("State: %s", state)  # Good
logger.debug(f"State: {state}")   # Bad - always evaluates
```

---

## 4. File I/O

### 4.1 Path Handling
```python
from pathlib import Path

# ✅ Always use pathlib
config_path = Path("data") / "config.json"

# ✅ Create directories safely
output_dir.mkdir(parents=True, exist_ok=True)

# ❌ Don't use string concatenation
path = "data" + "/" + "config.json"  # Wrong
```

### 4.2 Atomic Writes
```python
import tempfile
import shutil

def save_state(state: State, path: Path) -> None:
    """Save state atomically."""
    # Write to temp file first
    temp_fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=".state_",
        suffix=".tmp",
    )
    try:
        with os.fdopen(temp_fd, "w") as f:
            json.dump(state.model_dump(), f, indent=2)
        # Atomic rename
        shutil.move(temp_path, path)
    except Exception:
        # Clean up temp file on error
        Path(temp_path).unlink(missing_ok=True)
        raise
```

### 4.3 JSON Handling
```python
import json
from datetime import datetime

# ✅ Custom encoder for datetime
class PodStockEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Path):
            return str(obj)
        return super().default(obj)

# ✅ Usage
json.dump(data, f, cls=PodStockEncoder, indent=2, ensure_ascii=False)
```

---

## 5. Testing

### 5.1 Test Structure
```python
# tests/test_rss_parser.py

import pytest
from pathlib import Path

from podstock.rss.parser import parse_episode, fetch_feed
from podstock.core.models import Episode

# Fixtures
@pytest.fixture
def sample_feed_path() -> Path:
    return Path(__file__).parent / "fixtures" / "sample_rss.xml"

@pytest.fixture
def sample_feed(sample_feed_path: Path) -> str:
    return sample_feed_path.read_text()

# Tests grouped by function
class TestParseEpisode:
    def test_parses_title(self, sample_item):
        episode = parse_episode(sample_item)
        assert episode.title == "Avsnitt 598"
    
    def test_parses_date(self, sample_item):
        episode = parse_episode(sample_item)
        assert episode.published_at.year == 2024
    
    def test_handles_missing_duration(self, sample_item_no_duration):
        episode = parse_episode(sample_item_no_duration)
        assert episode.duration_seconds is None

class TestFetchFeed:
    def test_fetches_valid_feed(self, mock_rss_server):
        feed = fetch_feed(mock_rss_server.url)
        assert len(feed.entries) > 0
    
    def test_raises_on_invalid_url(self):
        with pytest.raises(RSSError):
            fetch_feed("https://invalid.example.com/rss")
```

### 5.2 Test Naming
```python
# ✅ Descriptive names
def test_download_creates_file_in_correct_directory():
    ...

def test_download_skips_existing_file_when_not_overwrite():
    ...

def test_download_raises_on_network_timeout():
    ...

# ❌ Vague names
def test_download():
    ...

def test_error():
    ...
```

### 5.3 Mocking
```python
from unittest.mock import Mock, patch

def test_transcribe_calls_whisper_with_correct_model():
    with patch("podstock.transcribe.whisper.mlx_whisper") as mock_whisper:
        mock_whisper.transcribe.return_value = {"text": "Hello"}
        
        result = transcribe(Path("test.mp3"), model="small")
        
        mock_whisper.transcribe.assert_called_once()
        call_args = mock_whisper.transcribe.call_args
        assert call_args.kwargs["model"] == "small"
```

---

## 6. CLI Design

### 6.1 Command Structure
```python
# ✅ Consistent command patterns
podstock <noun> <verb> [options]

podstock podcast add <name> <url>
podstock podcast list
podstock episode download --podcast <id>
podstock episode transcribe <id>

# ✅ Common flags
--verbose, -v    # Increase output verbosity
--quiet, -q      # Suppress non-error output
--force, -f      # Override safety checks
--dry-run        # Show what would happen
```

### 6.2 Output
```python
from rich.console import Console
from rich.table import Table

console = Console()

# ✅ Structured output
table = Table(title="Podcasts")
table.add_column("ID")
table.add_column("Name")
table.add_column("Episodes")

for podcast in podcasts:
    table.add_row(podcast.id, podcast.name, str(podcast.episode_count))

console.print(table)

# ✅ Progress bars for long operations
from rich.progress import Progress

with Progress() as progress:
    task = progress.add_task("Downloading...", total=file_size)
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)
        progress.update(task, advance=len(chunk))
```

---

## 7. Git Conventions

### 7.1 Commit Messages
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code change that neither fixes nor adds
- `docs`: Documentation only
- `test`: Adding tests
- `chore`: Maintenance

Examples:
```
feat(rss): add support for Acast RSS format

fix(download): handle network timeout gracefully

refactor(models): extract validation to separate module

docs(readme): add installation instructions
```

### 7.2 Branch Naming
```
feature/add-podcast-command
fix/download-timeout
refactor/models-validation
```

---

## 8. Security

### 8.1 No Secrets in Code
```python
# ❌ Never
API_KEY = "sk-abc123..."

# ✅ Use environment or config
api_key = os.environ.get("ANTHROPIC_API_KEY")
```

### 8.2 Input Validation
```python
# ✅ Validate all external input
def add_podcast(name: str, url: str) -> Podcast:
    # Validate URL
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"Invalid URL: {url}")
    
    # Sanitize name
    safe_name = re.sub(r"[^\w\s-]", "", name)
    
    # Validate RSS actually works
    try:
        feed = fetch_feed(url)
    except Exception as e:
        raise RSSError(f"Could not fetch RSS: {e}")
    
    ...
```

---

## 9. Performance

### 9.1 Memory
```python
# ✅ Stream large files
def download_large_file(url: str, dest: Path) -> None:
    with requests.get(url, stream=True) as r:
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

# ❌ Don't load entire file into memory
content = requests.get(url).content  # Bad for large files
```

### 9.2 Lazy Loading
```python
# ✅ Load data only when needed
class TranscriptStore:
    def __init__(self, path: Path):
        self._path = path
        self._cache: dict[str, str] = {}
    
    def get(self, episode_id: str) -> str:
        if episode_id not in self._cache:
            self._cache[episode_id] = self._load(episode_id)
        return self._cache[episode_id]
```
