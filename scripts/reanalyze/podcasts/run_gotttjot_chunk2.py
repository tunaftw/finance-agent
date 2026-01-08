#!/usr/bin/env python3
"""
Runner för Gotttjot (chunk 2: avsnitt 51-61).
Genererad automatiskt - kör med: python3 run_gotttjot_chunk2.py
"""

import sys
from pathlib import Path

# Lägg till scripts-mappen i path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner import PodcastRunner

if __name__ == "__main__":
    runner = PodcastRunner(
        podcast_id="gotttjot",
        chunk=(50, 61)
    )
    runner.run()
