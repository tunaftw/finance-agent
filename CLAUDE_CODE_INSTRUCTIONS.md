# PodStock – Claude Code Instructions

**Version:** 1.0  
**Datum:** 2024-12-21

---

## 🎯 Purpose of This Document

Detta dokument är **den primära guiden** för Claude Code när du arbetar på PodStock-projektet. Läs detta dokument FÖRST innan du gör något annat.

---

## 📋 Quick Reference

| Document | Purpose |
|----------|---------|
| `PRD.md` | Vad ska byggas och varför |
| `ARCHITECTURE.md` | Hur systemet är strukturerat |
| `IMPLEMENTATION.md` | **Checklista** - uppdatera denna löpande! |
| `CONVENTIONS.md` | Kodstil och best practices |
| `CLAUDE_CODE_INSTRUCTIONS.md` | Detta dokument - hur du ska arbeta |

---

## 🔴 KRITISKA REGLER

### 1. Uppdatera IMPLEMENTATION.md efter varje uppgift
```markdown
# Efter att du implementerat något:
1. Öppna IMPLEMENTATION.md
2. Checka av relevanta punkter: [ ] → [x]
3. Lägg till datum
4. Notera eventuella avvikelser eller beslut
```

### 2. Skriv tester INNAN eller TILLSAMMANS med kod
```markdown
# Test-Driven Development (TDD) flow:
1. Skriv ett failing test
2. Implementera minimal kod för att passa testet
3. Refaktorera
4. Repeat
```

### 3. Commita ofta med tydliga meddelanden
```markdown
# Commit efter varje logisk enhet:
- En funktion implementerad
- Ett test tillagt
- En bug fixad

# Exempel:
feat(rss): implement fetch_feed function
test(rss): add tests for parse_episode
fix(download): handle timeout correctly
```

### 4. Fråga vid osäkerhet
```markdown
# Om något är oklart:
1. Dokumentera frågan i IMPLEMENTATION.md under "Blockers & Open Questions"
2. Gör ett rimligt antagande och dokumentera det
3. Fortsätt med nästa uppgift om möjligt
```

---

## 🚀 Hur du startar ett nytt arbetspass

### Steg 1: Orientera dig
```bash
# Läs igenom nuvarande status
cat IMPLEMENTATION.md | head -100

# Se vad som är klart och vad som är nästa
grep -n "\[ \]" IMPLEMENTATION.md | head -20
```

### Steg 2: Välj nästa uppgift
```markdown
Prioriteringsordning:
1. Phase 0 (Setup) måste vara klart först
2. Phase 1 (Core) innan Phase 2-5
3. Phase 6 (CLI) kan påbörjas parallellt med Phase 2-5
4. Följ fasordningen inom varje fas

Om något är blockerat:
- Dokumentera i IMPLEMENTATION.md
- Hoppa till nästa oberoende uppgift
```

### Steg 3: Implementera
```markdown
För varje uppgift:
1. Läs relevant sektion i ARCHITECTURE.md
2. Skriv test först (eller parallellt)
3. Implementera kod
4. Kör tester: pytest tests/
5. Kör linter: ruff check src/
6. Kör type check: mypy src/
7. Commita
8. Uppdatera IMPLEMENTATION.md
```

---

## 📁 Filskapande - Steg för steg

### När du skapar en ny modul:

```python
# 1. Skapa filen med rätt header
"""Module description.

This module provides...
"""

from __future__ import annotations

# 2. Lägg till i __init__.py för modulen
# src/podstock/rss/__init__.py
from podstock.rss.parser import fetch_feed, parse_episode

# 3. Skapa motsvarande testfil
# tests/test_rss_parser.py

# 4. Uppdatera IMPLEMENTATION.md
```

### Exakt mappstruktur att följa:

```
podstock/
├── src/
│   └── podstock/
│       ├── __init__.py          # Version, public API
│       ├── __main__.py          # Entry: python -m podstock
│       ├── cli.py               # Argparse commands
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── exceptions.py
│       │   ├── models.py
│       │   └── state.py
│       ├── rss/
│       │   ├── __init__.py
│       │   ├── downloader.py
│       │   ├── manager.py
│       │   └── parser.py
│       ├── transcribe/
│       │   ├── __init__.py
│       │   └── whisper.py
│       ├── analyze/
│       │   ├── __init__.py
│       │   ├── prompt_builder.py
│       │   └── result_parser.py
│       └── report/
│           ├── __init__.py
│           └── markdown.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures
│   ├── test_models.py
│   ├── test_config.py
│   ├── test_rss_parser.py
│   └── fixtures/
│       ├── sample_rss_libsyn.xml
│       └── sample_rss_acast.xml
├── prompts/
│   └── analyze_transcript.md
├── data/                        # Gitignored
│   ├── config.json
│   ├── state.json
│   ├── podcasts.json
│   ├── audio/
│   ├── transcripts/
│   ├── recommendations/
│   └── reports/
├── pyproject.toml
├── requirements.txt
├── README.md
├── PRD.md
├── ARCHITECTURE.md
├── IMPLEMENTATION.md
├── CONVENTIONS.md
└── CLAUDE_CODE_INSTRUCTIONS.md
```

---

## 🧪 Testning

### Köra tester
```bash
# Alla tester
pytest tests/

# Med coverage
pytest tests/ --cov=src/podstock --cov-report=term-missing

# Specifik testfil
pytest tests/test_rss_parser.py

# Specifikt test
pytest tests/test_rss_parser.py::TestFetchFeed::test_handles_timeout
```

### Testfil-template
```python
"""Tests for podstock.rss.parser module."""

import pytest
from pathlib import Path

from podstock.rss.parser import fetch_feed, parse_episode
from podstock.core.models import Episode
from podstock.core.exceptions import RSSError


@pytest.fixture
def sample_rss_path() -> Path:
    """Path to sample RSS fixture."""
    return Path(__file__).parent / "fixtures" / "sample_rss_libsyn.xml"


@pytest.fixture
def sample_rss_content(sample_rss_path: Path) -> str:
    """Content of sample RSS."""
    return sample_rss_path.read_text()


class TestParseEpisode:
    """Tests for parse_episode function."""
    
    def test_extracts_title(self, sample_rss_content):
        """Should extract episode title from RSS item."""
        # Arrange
        # ... parse RSS to get item
        
        # Act
        episode = parse_episode(item)
        
        # Assert
        assert episode.title == "Avsnitt 598 - Julspecial"
    
    def test_handles_missing_optional_fields(self):
        """Should handle missing optional fields gracefully."""
        ...
```

---

## 🔧 Vanliga uppgifter

### Lägga till en ny podcast i config

```json
// data/podcasts.json
{
  "podcasts": [
    {
      "id": "borspodden",
      "name": "Börspodden",
      "rss_url": "https://borspodden.libsyn.com/rss",
      "hosts": ["Johan Isaksson", "John Skogman"]
    },
    // ... etc
  ]
}
```

### Skapa pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "podstock"
version = "0.1.0"
description = "Track stock recommendations from Swedish podcasts"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "feedparser>=6.0.0",
    "requests>=2.28.0",
    "pydantic>=2.0.0",
    "rich>=13.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov",
    "ruff",
    "mypy",
]
transcribe = [
    "mlx-whisper>=0.1.0",
]

[project.scripts]
podstock = "podstock.cli:main"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.mypy]
python_version = "3.11"
strict = true
```

### Skapa requirements.txt

```
# Core
feedparser>=6.0.0
requests>=2.28.0
pydantic>=2.0.0
rich>=13.0.0

# Transcription (optional, install separately on M4 Mac)
# mlx-whisper>=0.1.0

# Development
pytest>=7.0.0
pytest-cov
ruff
mypy
```

---

## 🐛 Debugging

### Vanliga problem

**Problem: mlx-whisper fungerar inte**
```bash
# Verifiera M4/Apple Silicon
python -c "import platform; print(platform.processor())"

# Installera korrekt
pip install mlx-whisper

# Test
python -c "import mlx_whisper; print('OK')"
```

**Problem: RSS parsing misslyckas**
```python
# Debug med feedparser direkt
import feedparser
feed = feedparser.parse("https://borspodden.libsyn.com/rss")
print(feed.bozo)  # True = parsing error
print(feed.bozo_exception)  # Error details
```

**Problem: Tester hittar inte moduler**
```bash
# Installera i utvecklingsläge
pip install -e .

# Eller kör med python path
PYTHONPATH=src pytest tests/
```

---

## 📝 Templates

### Ny funktion template
```python
def function_name(
    required_arg: ArgType,
    optional_arg: ArgType | None = None,
    *,
    keyword_only: bool = False,
) -> ReturnType:
    """One-line description.
    
    Longer description if needed.
    
    Args:
        required_arg: Description.
        optional_arg: Description. Defaults to None.
        keyword_only: Description. Defaults to False.
    
    Returns:
        Description of return value.
    
    Raises:
        SpecificError: When this happens.
    
    Example:
        >>> result = function_name("input")
        >>> print(result)
    """
    # Validate input
    if not required_arg:
        raise ValueError("required_arg cannot be empty")
    
    # Main logic
    ...
    
    return result
```

### Ny klass template
```python
class ClassName:
    """One-line description.
    
    Longer description if needed.
    
    Attributes:
        attr1: Description.
        attr2: Description.
    
    Example:
        >>> obj = ClassName(config)
        >>> obj.do_something()
    """
    
    # Class constants
    DEFAULT_VALUE = 42
    
    def __init__(self, config: Config) -> None:
        """Initialize ClassName.
        
        Args:
            config: Application configuration.
        """
        self._config = config
        self._state: dict[str, Any] = {}
    
    def public_method(self) -> None:
        """Do something publicly visible."""
        self._private_helper()
    
    def _private_helper(self) -> None:
        """Internal helper method."""
        ...
    
    @property
    def some_property(self) -> str:
        """Description of property."""
        return self._state.get("key", "default")
```

---

## ✅ Checklista innan du avslutar ett arbetspass

```markdown
□ Alla nya filer har docstrings
□ Alla publika funktioner har type hints
□ Tester skrivna och passerar
□ ruff check visar inga errors
□ mypy visar inga errors (eller dokumenterade ignores)
□ IMPLEMENTATION.md uppdaterad
□ Alla ändringar committade
□ Commit messages följer konventionen
```

---

## 🆘 Om du kör fast

1. **Läs om relevant dokumentation** - PRD.md, ARCHITECTURE.md
2. **Kolla CONVENTIONS.md** för kodstil
3. **Dokumentera problemet** i IMPLEMENTATION.md under "Blockers"
4. **Gör ett antagande** och fortsätt - dokumentera antagandet
5. **Fråga användaren** om något är fundamentalt oklart

---

## 🎯 Mål för MVP

När MVP är klart ska följande fungera:

```bash
# 1. Visa konfigurerade podcasts
podstock podcast list

# 2. Ladda ner senaste avsnittet från en podcast
podstock download --podcast borspodden --latest 1

# 3. Transkribera det nedladdade avsnittet
podstock transcribe --podcast borspodden

# 4. Generera analys-prompt
podstock analyze bp-2024-12-18

# 5. (Manuellt) Kör prompten i Claude, spara svaret

# 6. Parsa Claude's svar
podstock analyze bp-2024-12-18 --input response.txt

# 7. Generera rapport
podstock report --output report.md
```

---

**Lycka till! Uppdatera IMPLEMENTATION.md löpande.**
