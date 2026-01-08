#!/usr/bin/env python3
"""
Runner för Analyspodden (chunk 6: avsnitt 251-300).
Genererad automatiskt - kör med: python3 run_analyspodden_chunk6.py
"""

import sys
from pathlib import Path

# Lägg till scripts-mappen i path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner import PodcastRunner

if __name__ == "__main__":
    runner = PodcastRunner(
        podcast_id="analyspodden",
        chunk=(250, 300)
    )
    runner.run()
