# Cache Logic

## Overview

FUNDAMENTA and SENTIMENT agents use cached analyses when available to:
1. Speed up analysis
2. Avoid redundant processing
3. Ensure consistency across runs

## SENTIMENT Cache

**Location**: `data/sentiment/{ticker}-analysis.json`

**Max age**: 7 days

**Check logic**:
```python
from pathlib import Path
from datetime import datetime
import json

cache_path = Path(f'data/sentiment/{ticker}-analysis.json')
if cache_path.exists():
    cached = json.loads(cache_path.read_text())
    analyzed_at = datetime.fromisoformat(cached['analyzed_at'].replace('Z', '+00:00'))
    age = (datetime.now(analyzed_at.tzinfo) - analyzed_at).days
    if age <= 7:
        # Ask user: use cached or refresh?
        return cached
```

**User prompt**:
```
Hittade cached sentiment-analys (X dagar gammal).
- Använd cached (snabbt)
- Kör ny analys (tar längre tid)
```

## FUNDAMENTA Cache

**Location**: `data/filings/analysis/{company}/*.json`

**Max age**: 90 days (reports are quarterly)

**Check logic**:
```python
analysis_dir = Path(f'data/filings/analysis/{company_slug}')
if analysis_dir.exists():
    analyses = sorted(analysis_dir.glob('*.json'))
    if analyses:
        latest = json.loads(analyses[-1].read_text())
        # Check age of latest analysis
```

## Cache Invalidation

Caches should be refreshed when:
1. New data arrives (new podcast episode, new quarterly report)
2. User explicitly requests refresh
3. Cache exceeds max age

## No-Cache Mode

User can bypass cache with context:
```
/alpha BETS-B "force refresh"
```

Agent should detect "force" or "refresh" in context and skip cache check.
