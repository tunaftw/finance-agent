#!/usr/bin/env python3
"""
Runner för Borsmaklarna (chunk 3: avsnitt 101-118).
Genererad automatiskt - kör med: python3 run_borsmaklarna_chunk3.py
"""

import sys
from pathlib import Path

# Lägg till scripts-mappen i path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner import PodcastRunner

if __name__ == "__main__":
    runner = PodcastRunner(
        podcast_id="borsmaklarna",
        chunk=(100, 118)
    )
    runner.run()
