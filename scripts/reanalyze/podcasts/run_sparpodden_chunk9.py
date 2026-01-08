#!/usr/bin/env python3
"""
Runner för Sparpodden (chunk 9: avsnitt 401-442).
Genererad automatiskt - kör med: python3 run_sparpodden_chunk9.py
"""

import sys
from pathlib import Path

# Lägg till scripts-mappen i path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner import PodcastRunner

if __name__ == "__main__":
    runner = PodcastRunner(
        podcast_id="sparpodden",
        chunk=(400, 442)
    )
    runner.run()
