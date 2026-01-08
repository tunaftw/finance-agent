#!/usr/bin/env python3
"""
Runner för Montrosepodden (chunk 2: avsnitt 51-87).
Genererad automatiskt - kör med: python3 run_montrosepodden_chunk2.py
"""

import sys
from pathlib import Path

# Lägg till scripts-mappen i path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner import PodcastRunner

if __name__ == "__main__":
    runner = PodcastRunner(
        podcast_id="montrosepodden",
        chunk=(50, 87)
    )
    runner.run()
