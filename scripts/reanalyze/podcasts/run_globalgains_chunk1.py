#!/usr/bin/env python3
"""
Runner för Globalgains (chunk 1: avsnitt 1-50).
Genererad automatiskt - kör med: python3 run_globalgains_chunk1.py
"""

import sys
from pathlib import Path

# Lägg till scripts-mappen i path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner import PodcastRunner

if __name__ == "__main__":
    runner = PodcastRunner(
        podcast_id="globalgains",
        chunk=(0, 50)
    )
    runner.run()
