#!/usr/bin/env python3
"""
Re-analys runner för Globalgains.

Kör med: python3 scripts/reanalyze/podcasts/run_globalgains.py
"""

import sys
from pathlib import Path

# Lägg till parent för import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from reanalyze.runner import run_podcast

if __name__ == "__main__":
    run_podcast("globalgains")
