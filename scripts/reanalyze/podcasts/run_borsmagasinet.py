#!/usr/bin/env python3
"""
Runner för Borsmagasinet.
Genererad automatiskt - kör med: python3 run_borsmagasinet.py
"""

import sys
from pathlib import Path

# Lägg till scripts-mappen i path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runner import PodcastRunner

if __name__ == "__main__":
    runner = PodcastRunner(
        podcast_id="borsmagasinet",
        chunk=None
    )
    runner.run()
