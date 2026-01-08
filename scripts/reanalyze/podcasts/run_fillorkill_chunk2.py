#!/usr/bin/env python3
"""
Runner för Fillorkill (chunk 2: avsnitt 51-100).
Genererad automatiskt - kör med: python3 run_fillorkill_chunk2.py
"""

import sys
from pathlib import Path

# Lägg till scripts-mappen i path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner import PodcastRunner

if __name__ == "__main__":
    runner = PodcastRunner(
        podcast_id="fillorkill",
        chunk=(50, 100)
    )
    runner.run()
