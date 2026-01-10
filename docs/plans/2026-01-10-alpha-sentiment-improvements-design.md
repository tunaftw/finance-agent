# Alpha Skill Improvements: Comprehensive Sentiment Integration

## Problem Statement

The current Alpha skill:
1. Does not systematically include all available podcast/Twitter/YouTube data in analysis
2. May skip relevant sources without explicit documentation
3. Takes podcast claims at face value without critical evaluation
4. Attempts to read PDFs directly, causing context overflow crashes
5. Lacks structured confidence scoring for recommendations

## Design Goals

1. **Every data source explicitly considered** - even if ultimately ignored after review
2. **Transparent triage** - documented reasoning for what was included/excluded
3. **Critical evaluation** - podcast claims are opinions, not facts
4. **Confidence scoring** - structured scoring for recommendations/quotes
5. **Dashboard-compatible output** - rich JSON that renders on existing dashboard
6. **Robust PDF handling** - chunked processing that doesn't crash

---

## Architecture Overview

```
/alpha <company>
    │
    ├── Step 1: Data Inventory (unchanged)
    │
    ├── Step 2: Parallel Agents
    │   ├── FUNDAMENTA → calls analyze-filings skill (cached)
    │   ├── SENTIMENT → calls NEW analyze-sentiment skill (cached)
    │   ├── INSIDER → unchanged
    │   └── EXTERN → unchanged
    │
    ├── Step 3: RISKER Agent (after parallel agents)
    │
    └── Step 4: Synthesis & Output
```

### Key Changes

1. **FUNDAMENTA agent** now calls `analyze-filings` skill instead of reading PDFs directly
2. **SENTIMENT agent** now calls new `analyze-sentiment` skill
3. Both check for cached analysis first, ask to use/update

---

## New Skill: analyze-sentiment

### Purpose

Aggregate all sentiment data for a specific company from multiple sources:
- Podcast analyses (JSON)
- Podcast transcripts (raw)
- Twitter threads
- YouTube analyses
- Press releases (non-financial ones)

### Workflow

```
1. GATHER: Find all sources mentioning company
2. TRIAGE: Explicit review of each source
3. EXTRACT: Pull quotes, recommendations, facts
4. SCORE: Apply confidence scoring
5. AGGREGATE: Combine into structured output
6. SAVE: Cache to data/sentiment/{ticker}-analysis.json
```

### Triage Rules

| Source Type | Primary Use | Treatment |
|-------------|-------------|-----------|
| Press releases (financial) | Facts → FUNDAMENTA | Extract data points |
| Press releases (other) | Timeline → SENTIMENT | As newsflow |
| Podcast analyses (JSON) | Sentiment | Extract recommendations |
| Podcast transcripts | Deep context | Search for specific claims |
| Twitter threads | Real-time sentiment | Weight by author credibility |
| YouTube analyses | Sentiment | Similar to podcasts |

### Confidence Scoring

Each quote/recommendation gets a score from 4 criteria (1-3 points each):

| Criterion | 1 point | 2 points | 3 points |
|-----------|---------|----------|----------|
| **Specificity** | Vague ("might be good") | Moderate ("looks attractive") | Precise ("buy under 25 SEK") |
| **Reasoning** | Opinion only | Some rationale | Full thesis with numbers |
| **Risk-awareness** | No risks mentioned | Some caveats | Explicit bear case |
| **Recency** | >6 months old | 1-6 months | <1 month |

**Total: 4-12 points**

| Score | Label |
|-------|-------|
| 10-12 | High confidence |
| 7-9 | Medium confidence |
| 4-6 | Low confidence |

### Output Schema

```json
{
  "ticker": "CARA",
  "analyzed_at": "2026-01-10T12:00:00Z",
  "sources_reviewed": 45,
  "sources_analyzed": 28,
  "sources_ignored": 17,

  "triage_summary": {
    "podcasts_reviewed": 26,
    "podcasts_analyzed": 18,
    "podcasts_ignored": 8,
    "twitter_reviewed": 0,
    "press_releases_reviewed": 25,
    "press_releases_to_fundamenta": 12,
    "press_releases_to_timeline": 13
  },

  "triage_log": [
    {
      "source_id": "borsens-finest-2024-01-15",
      "source_type": "podcast",
      "decision": "ignored",
      "reason": "No mention of CARA in transcript"
    },
    {
      "source_id": "analyspodden-326",
      "source_type": "podcast",
      "decision": "analyzed",
      "reason": "CEO interview + analyst coverage"
    }
  ],

  "quotes": [
    {
      "id": "q1",
      "text": "Carasent är en turnaround-story med låg churn och stark recurring revenue",
      "speaker": "Per Johansson",
      "affiliation": "Origo Capital",
      "source": "Börsens Finest 2025-11-05",
      "source_type": "podcast",
      "date": "2025-11-05",
      "context": "Discussion about healthcare IT sector",
      "stance": "bullish",
      "owns_position": true,
      "confidence_score": {
        "specificity": 2,
        "reasoning": 2,
        "risk_awareness": 1,
        "recency": 3,
        "total": 8,
        "label": "medium"
      },
      "extracted_claims": [
        {"claim": "Low churn", "type": "fact", "verifiable": true},
        {"claim": "Strong recurring revenue", "type": "opinion"}
      ]
    }
  ],

  "notable_speakers": [
    {
      "name": "Per Johansson",
      "affiliation": "Origo Capital",
      "stance": "bullish",
      "owns_position": true,
      "argument": "Turnaround story, strong recurring revenue, low churn",
      "quote": "Carasent är en turnaround-story...",
      "source": "Börsens Finest 2025-11-05",
      "confidence_score": 8
    }
  ],

  "bull_arguments": [
    "Low churn (2% annually) = sticky recurring revenue",
    "German expansion opportunity (150K private clinics)",
    "Management turnaround track record since 2022"
  ],

  "bear_arguments": [
    "CEO sold shares after profit warning - alignment concern",
    "Organic growth 13% below 15%+ target",
    "VGR contract concentration risk"
  ],

  "overall_score": 7.5,
  "label": "bullish",
  "trend": "stable",

  "summary": "Market sentiment bullish with multiple BUY recommendations..."
}
```

---

## Integration with Alpha Skill

### Modified SENTIMENT Agent Prompt

```
Du är SENTIMENT-agenten i Alpha-analysen.

UPPDRAG: Samla och kritiskt utvärdera all sentiment-data för {company}.

STEG 1: Kör analyze-sentiment skill
- Kolla först om cached analys finns: data/sentiment/{ticker}-analysis.json
- Om finns och <7 dagar gammal: fråga användaren om den ska användas
- Annars: kör analyze-sentiment skill

STEG 2: Kritisk granskning
- Podcast-påståenden är ÅSIKTER, inte fakta
- Verifiera påståenden mot fundamenta där möjligt
- Flagga motstridiga åsikter
- Notera vem som äger aktier (bias-risk)

STEG 3: Syntes
- Sammanfatta bull/bear-argument
- Identifiera notabla speakers
- Beräkna overall sentiment score
```

### Modified FUNDAMENTA Agent Prompt

```
Du är FUNDAMENTA-agenten i Alpha-analysen.

UPPDRAG: Analysera finansiella rapporter för {company}.

STEG 1: Kolla cached analys
- Sök i: data/filings/analysis/{company}/
- Om finns och relevant: använd den
- Annars: kör analyze-filings skill (delegerar PDF-läsning)

STEG 2: Extrahera nyckeltal
- Revenue, margins, cash flow
- CEO letter sentiment
- Red/green flags
- Quality score
```

---

## Dashboard Compatibility

### Existing Fields (unchanged)
```json
{
  "sentiment": {
    "overall_score": 7.5,
    "label": "bullish",
    "trend": "stable",
    "notable_speakers": [...],
    "bull_arguments": [...],
    "bear_arguments": [...],
    "summary": "..."
  }
}
```

### New Fields (additive)
```json
{
  "sentiment": {
    // ... existing fields ...

    "triage_summary": {
      "sources_reviewed": 45,
      "sources_analyzed": 28,
      "sources_ignored": 17
    },

    "quotes": [
      {
        "text": "...",
        "speaker": "...",
        "confidence_score": { "total": 8, "label": "medium" },
        // ... full quote object
      }
    ],

    "triage_log": [
      // Optional: can be excluded from dashboard export to save space
    ]
  }
}
```

### Dashboard UI Enhancement (optional)

Add expandable "Quotes" section in sentiment view:

```html
<!-- Quotes Section (new) -->
<div x-show="currentAlphaAnalysis?.sentiment?.quotes?.length"
     class="bg-gray-800 rounded-lg p-4 border border-gray-700">
    <h4 class="font-medium mb-3">Quotes & Recommendations</h4>
    <div class="space-y-2">
        <template x-for="quote in currentAlphaAnalysis?.sentiment?.quotes" :key="quote.id">
            <div class="p-3 bg-gray-700/50 rounded-lg" x-data="{ expanded: false }">
                <div class="flex items-center justify-between cursor-pointer" @click="expanded = !expanded">
                    <div>
                        <span class="font-medium" x-text="quote.speaker"></span>
                        <span class="text-xs text-gray-400 ml-2" x-text="quote.date"></span>
                    </div>
                    <div class="flex items-center gap-2">
                        <span :class="[
                            'px-2 py-0.5 rounded text-xs',
                            quote.confidence_score.label === 'high' ? 'bg-green-600' : '',
                            quote.confidence_score.label === 'medium' ? 'bg-yellow-600' : '',
                            quote.confidence_score.label === 'low' ? 'bg-red-600' : ''
                        ]" x-text="quote.confidence_score.total + '/12'"></span>
                        <span x-text="expanded ? '▲' : '▼'" class="text-gray-400"></span>
                    </div>
                </div>
                <div x-show="expanded" x-collapse class="mt-2 text-sm text-gray-300">
                    <p class="italic" x-text="'\"' + quote.text + '\"'"></p>
                    <p class="text-xs text-gray-400 mt-1" x-text="'Källa: ' + quote.source"></p>
                </div>
            </div>
        </template>
    </div>
</div>
```

---

## Cache Logic

### analyze-sentiment Cache Check

```python
def get_sentiment_analysis(ticker: str, force_refresh: bool = False):
    cache_path = f"data/sentiment/{ticker}-analysis.json"

    if Path(cache_path).exists() and not force_refresh:
        cached = json.loads(Path(cache_path).read_text())
        age_days = (datetime.now() - datetime.fromisoformat(cached['analyzed_at'])).days

        if age_days < 7:
            # Ask user
            return {"status": "cached", "age_days": age_days, "data": cached}

    # Run full analysis
    return {"status": "needs_analysis"}
```

### analyze-filings Cache Check

```python
def get_filings_analysis(company_slug: str):
    analysis_dir = Path(f"data/filings/analysis/{company_slug}")

    if analysis_dir.exists():
        latest = sorted(analysis_dir.glob("*.json"))[-1]
        return {"status": "cached", "path": str(latest)}

    return {"status": "needs_analysis"}
```

---

## Implementation Plan

### Phase 1: Create analyze-sentiment skill
1. Create skill directory: `.claude/skills/analyze-sentiment/`
2. Write SKILL.md with workflow
3. Define output schema in references/
4. Implement triage logic
5. Implement confidence scoring

### Phase 2: Update Alpha skill
1. Modify SENTIMENT agent to call analyze-sentiment
2. Modify FUNDAMENTA agent to call analyze-filings
3. Add cache-check prompts
4. Update output merging logic

### Phase 3: Dashboard (optional)
1. Add quotes section to sentiment view
2. Add triage summary display
3. Sortable by date/confidence

---

## Verification Checklist

- [ ] All podcast sources are explicitly triaged
- [ ] Confidence scores calculated correctly
- [ ] Cached analysis is reused appropriately
- [ ] New fields don't break existing dashboard
- [ ] PDFs processed without context overflow
- [ ] Press releases routed correctly (financial → FUNDAMENTA, other → timeline)
