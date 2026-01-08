#!/usr/bin/env python3
"""
Runner för Aktiepodden (chunk 5: avsnitt 201-244).
Genererad automatiskt - kör med: python3 run_aktiepodden_chunk5.py
"""

import sys
from pathlib import Path

# Lägg till scripts-mappen i path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner import PodcastRunner

if __name__ == "__main__":
    runner = PodcastRunner(
        podcast_id="aktiepodden",
        chunk=(200, 244)
    )
    runner.run()
