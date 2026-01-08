#!/usr/bin/env python3
"""
Runner för Marketmakers (chunk 5: avsnitt 201-250).
Genererad automatiskt - kör med: python3 run_marketmakers_chunk5.py
"""

import sys
from pathlib import Path

# Lägg till scripts-mappen i path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner import PodcastRunner

if __name__ == "__main__":
    runner = PodcastRunner(
        podcast_id="marketmakers",
        chunk=(200, 250)
    )
    runner.run()
