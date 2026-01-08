#!/usr/bin/env python3
"""
Runner för Marknaden (chunk 3: avsnitt 101-150).
Genererad automatiskt - kör med: python3 run_marknaden_chunk3.py
"""

import sys
from pathlib import Path

# Lägg till scripts-mappen i path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner import PodcastRunner

if __name__ == "__main__":
    runner = PodcastRunner(
        podcast_id="marknaden",
        chunk=(100, 150)
    )
    runner.run()
