#!/usr/bin/env python3
"""
Runner för Ettrikareliv (chunk 3: avsnitt 101-108).
Genererad automatiskt - kör med: python3 run_ettrikareliv_chunk3.py
"""

import sys
from pathlib import Path

# Lägg till scripts-mappen i path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner import PodcastRunner

if __name__ == "__main__":
    runner = PodcastRunner(
        podcast_id="ettrikareliv",
        chunk=(100, 108)
    )
    runner.run()
