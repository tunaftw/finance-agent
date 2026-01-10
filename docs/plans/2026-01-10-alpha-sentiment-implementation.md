# Alpha Sentiment Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create `analyze-sentiment` skill and update Alpha to use it for comprehensive, transparent sentiment analysis.

**Architecture:** New skill aggregates all sentiment sources with explicit triage and confidence scoring. Alpha's SENTIMENT agent calls this skill (cached). FUNDAMENTA agent updated to call existing analyze-filings skill.

**Tech Stack:** Claude Code skills (markdown), JSON schemas, Task tool for agents

---

## Task 1: Create analyze-sentiment Skill Directory Structure

**Files:**
- Create: `.claude/skills/analyze-sentiment/SKILL.md`
- Create: `.claude/skills/analyze-sentiment/references/output-schema.md`
- Create: `.claude/skills/analyze-sentiment/references/triage-rules.md`
- Create: `.claude/skills/analyze-sentiment/references/confidence-scoring.md`

**Step 1: Create skill directory**

```bash
mkdir -p .claude/skills/analyze-sentiment/references
```

**Step 2: Verify directory created**

Run: `ls -la .claude/skills/analyze-sentiment/`
Expected: Empty directory with references subdirectory

**Step 3: Commit directory structure**

```bash
git add .claude/skills/analyze-sentiment/
git commit -m "chore: create analyze-sentiment skill directory"
```

---

## Task 2: Write analyze-sentiment SKILL.md

**Files:**
- Create: `.claude/skills/analyze-sentiment/SKILL.md`

**Step 1: Write SKILL.md with complete workflow**

```markdown
---
name: analyze-sentiment
description: Aggregera all sentiment-data för ett bolag från podcasts, Twitter, YouTube och pressmeddelanden. Explicit triage av alla källor med confidence scoring.
---

# Analyze Sentiment

Samla och kritiskt utvärdera all sentiment-data för ett specifikt bolag.

## Quick Start

```
/analyze-sentiment CARA
/analyze-sentiment Betsson "senaste 6 mån"
```

## Kärnprinciper

- **Explicit triage** - varje källa granskas och beslut dokumenteras
- **Kritisk granskning** - podcast-påståenden är åsikter, inte fakta
- **Confidence scoring** - strukturerad poängsättning av rekommendationer
- **Cache-aware** - använd befintlig analys om tillräckligt färsk

---

## Workflow

### Step 1: Check Cache

```python
from pathlib import Path
from datetime import datetime
import json

def check_sentiment_cache(ticker: str, max_age_days: int = 7):
    cache_path = Path(f'data/sentiment/{ticker}-analysis.json')

    if not cache_path.exists():
        return {"status": "needs_analysis", "path": str(cache_path)}

    cached = json.loads(cache_path.read_text())
    analyzed_at = datetime.fromisoformat(cached['analyzed_at'].replace('Z', '+00:00'))
    age_days = (datetime.now(analyzed_at.tzinfo) - analyzed_at).days

    if age_days <= max_age_days:
        return {
            "status": "cached",
            "age_days": age_days,
            "data": cached,
            "path": str(cache_path)
        }

    return {"status": "stale", "age_days": age_days, "path": str(cache_path)}
```

Om cached och färsk: fråga användaren om den ska användas eller uppdateras.

### Step 2: Gather Sources

Samla ALLA källor som nämner bolaget:

```python
def gather_sources(ticker: str, company_name: str):
    sources = {
        "podcasts": [],      # data/podcasts/analyses-v2/*.json
        "transcripts": [],   # data/transcripts/*/*.txt (för djupdykning)
        "twitter": [],       # data/twitter/analyses/*.json
        "youtube": [],       # data/youtube/analyses/*.json
        "press_releases": [] # data/news/raw/{company}/press-releases/*.json
    }

    # Sök i podcast-analyser efter ticker/company mentions
    for analysis_file in Path('data/podcasts/analyses-v2').glob('*.json'):
        analysis = json.loads(analysis_file.read_text())
        mentions = [r for r in analysis.get('recommendations', [])
                   if ticker in r.get('ticker', '') or
                      company_name.lower() in r.get('stock_name', '').lower()]
        if mentions:
            sources['podcasts'].append({
                "file": str(analysis_file),
                "episode_id": analysis.get('episode_id'),
                "date": analysis.get('date'),
                "mentions": mentions
            })

    # Similar logic for twitter, youtube, press releases...
    return sources
```

### Step 3: Triage Each Source

För varje källa, fatta explicit beslut:

| Decision | Meaning |
|----------|---------|
| `analyzed` | Relevant, inkluderas i analys |
| `ignored` | Granskad men inte relevant |
| `to_fundamenta` | Finansiell info, skickas till FUNDAMENTA |

Se: `references/triage-rules.md`

### Step 4: Extract Quotes & Recommendations

För varje `analyzed` källa, extrahera:
- Citat (exakt text)
- Talare (namn, affiliation)
- Stance (bullish/bearish/neutral)
- Äger position? (bias-flagga)
- Claims (fakta vs åsikter)

### Step 5: Apply Confidence Scoring

Varje quote får poäng på 4 kriterier (1-3 per kriterie):

| Kriterie | 1p | 2p | 3p |
|----------|----|----|-------|
| Specificity | Vag | Moderat | Precis |
| Reasoning | Bara åsikt | Viss logik | Full tes med siffror |
| Risk-awareness | Inga risker | Vissa förbehåll | Explicit bear case |
| Recency | >6 mån | 1-6 mån | <1 mån |

Total: 4-12 poäng → High (10-12), Medium (7-9), Low (4-6)

Se: `references/confidence-scoring.md`

### Step 6: Aggregate & Synthesize

Kombinera till:
- `notable_speakers[]` - de viktigaste rösterna
- `bull_arguments[]` - sammanfattade bull-argument
- `bear_arguments[]` - sammanfattade bear-argument
- `quotes[]` - alla citat med scoring
- `overall_score` - viktat sentiment (0-10)
- `label` - bullish/neutral/bearish

### Step 7: Save Analysis

```python
output_path = Path(f'data/sentiment/{ticker}-analysis.json')
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=False))
```

---

## Output Schema

Se: `references/output-schema.md`

---

## Integration med Alpha

Alpha's SENTIMENT agent kallar denna skill:

```
1. Kolla cache: check_sentiment_cache(ticker)
2. Om cached och färsk: fråga användaren
3. Om needs_analysis: kör full workflow
4. Returnera strukturerad sentiment-data till Alpha
```

---

## Exempel

```
User: /analyze-sentiment CARA

Claude: Kollar cache...
        Ingen befintlig analys hittad.

        Samlar källor...
        - Podcasts: 26 episoder med CARA-omnämnanden
        - Press releases: 25 pressmeddelanden
        - Twitter: 0 konton

        Triagar källor...
        - 18 podcasts analyserade
        - 8 podcasts ignorerade (inget substantiellt)
        - 12 PRs till FUNDAMENTA (finansiella)
        - 13 PRs till timeline

        Extraherar quotes...
        - 12 quotes med confidence scoring

        Sparar till: data/sentiment/CARA-analysis.json

        Sammanfattning:
        Overall: BULLISH (7.5/10)
        Notable speakers: Per Johansson (Origo), Carnegie Analyst
        Top quote: "Turnaround story med låg churn" (8/12 confidence)
```
```

**Step 2: Save file**

Write to: `.claude/skills/analyze-sentiment/SKILL.md`

**Step 3: Verify file created**

Run: `head -30 .claude/skills/analyze-sentiment/SKILL.md`
Expected: Frontmatter with name and description visible

**Step 4: Commit**

```bash
git add .claude/skills/analyze-sentiment/SKILL.md
git commit -m "feat(skill): add analyze-sentiment main skill file"
```

---

## Task 3: Write Output Schema Reference

**Files:**
- Create: `.claude/skills/analyze-sentiment/references/output-schema.md`

**Step 1: Write output schema**

```markdown
# Output Schema

## Complete Analysis Structure

```json
{
  "ticker": "CARA",
  "company_name": "Carasent AB",
  "analyzed_at": "2026-01-10T12:00:00Z",

  "triage_summary": {
    "sources_reviewed": 45,
    "sources_analyzed": 28,
    "sources_ignored": 17,
    "podcasts_reviewed": 26,
    "podcasts_analyzed": 18,
    "podcasts_ignored": 8,
    "twitter_reviewed": 0,
    "youtube_reviewed": 0,
    "press_releases_reviewed": 25,
    "press_releases_to_fundamenta": 12,
    "press_releases_to_timeline": 13
  },

  "triage_log": [
    {
      "source_id": "analyspodden-326",
      "source_type": "podcast",
      "date": "2025-03-30",
      "decision": "analyzed",
      "reason": "CEO interview + Carnegie analyst coverage"
    },
    {
      "source_id": "borsens-finest-2024-01-15",
      "source_type": "podcast",
      "date": "2024-01-15",
      "decision": "ignored",
      "reason": "Only brief mention, no substantive analysis"
    }
  ],

  "quotes": [
    {
      "id": "q1",
      "text": "Carasent är en turnaround-story med låg churn och stark recurring revenue",
      "speaker": "Per Johansson",
      "affiliation": "Origo Capital",
      "source_id": "borsens-finest-2025-11-05",
      "source_type": "podcast",
      "date": "2025-11-05",
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
        {
          "claim": "Low churn",
          "type": "fact",
          "verifiable": true,
          "verified": null
        },
        {
          "claim": "Strong recurring revenue",
          "type": "opinion",
          "verifiable": false
        }
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

  "summary": "Market sentiment bullish with multiple BUY recommendations from notable voices. However, CEO share sale after profit warning creates mixed signals."
}
```

## Field Descriptions

### triage_summary

| Field | Type | Description |
|-------|------|-------------|
| sources_reviewed | int | Total sources checked |
| sources_analyzed | int | Sources included in analysis |
| sources_ignored | int | Sources reviewed but excluded |

### quotes[]

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique quote identifier |
| text | string | Exact quote text |
| speaker | string | Person quoted |
| affiliation | string | Company/fund/role |
| owns_position | bool | Bias flag - speaker owns stock |
| confidence_score | object | Structured scoring (see below) |

### confidence_score

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| specificity | int | 1-3 | How precise is the recommendation |
| reasoning | int | 1-3 | Quality of rationale provided |
| risk_awareness | int | 1-3 | Mentions downsides/risks |
| recency | int | 1-3 | How recent is the statement |
| total | int | 4-12 | Sum of above |
| label | string | high/medium/low | Derived from total |
```

**Step 2: Save file**

Write to: `.claude/skills/analyze-sentiment/references/output-schema.md`

**Step 3: Commit**

```bash
git add .claude/skills/analyze-sentiment/references/output-schema.md
git commit -m "feat(skill): add analyze-sentiment output schema"
```

---

## Task 4: Write Triage Rules Reference

**Files:**
- Create: `.claude/skills/analyze-sentiment/references/triage-rules.md`

**Step 1: Write triage rules**

```markdown
# Triage Rules

## Decision Matrix

| Source Type | Primary Use | Decision Logic |
|-------------|-------------|----------------|
| Podcast analysis | Sentiment | analyzed if substantive mention |
| Podcast transcript | Deep context | analyzed only if analysis insufficient |
| Twitter thread | Real-time | analyzed if stock-specific |
| YouTube analysis | Sentiment | analyzed if substantive |
| Press release (financial) | Facts | to_fundamenta |
| Press release (other) | Timeline | analyzed as newsflow |

## Podcast Triage

**analyzed** when:
- Contains explicit recommendation (buy/sell/hold)
- Speaker provides reasoning/thesis
- Mentions specific metrics or catalysts
- CEO/company representative interview

**ignored** when:
- Only brief name-drop without substance
- Old (>12 months) with no unique insight
- Generic sector commentary
- Duplicate of another analyzed source

## Press Release Triage

**to_fundamenta** when:
- Quarterly/annual report
- Revenue/earnings update
- Guidance update
- Financial targets revision

**analyzed (timeline)** when:
- Partnership announcement
- Product launch
- Geographic expansion
- Management change
- Regulatory update

## Confidence Thresholds

For a quote to be included in `notable_speakers`:
- Confidence score >= 7 (medium or high)
- OR speaker is CEO/CFO of the company
- OR speaker is known fund manager with position

## Logging Format

Every source MUST have a triage log entry:

```json
{
  "source_id": "unique-identifier",
  "source_type": "podcast|twitter|youtube|press_release",
  "date": "YYYY-MM-DD",
  "decision": "analyzed|ignored|to_fundamenta",
  "reason": "Brief explanation (max 100 chars)"
}
```
```

**Step 2: Save file and commit**

```bash
git add .claude/skills/analyze-sentiment/references/triage-rules.md
git commit -m "feat(skill): add analyze-sentiment triage rules"
```

---

## Task 5: Write Confidence Scoring Reference

**Files:**
- Create: `.claude/skills/analyze-sentiment/references/confidence-scoring.md`

**Step 1: Write confidence scoring guide**

```markdown
# Confidence Scoring

## Scoring Criteria

### 1. Specificity (1-3)

How precise is the recommendation?

| Score | Examples |
|-------|----------|
| 1 | "Might be interesting", "Could be worth a look" |
| 2 | "Looks attractive", "I like this company" |
| 3 | "Buy under 25 SEK", "Target 40 SEK within 12 months" |

### 2. Reasoning (1-3)

Quality of rationale provided?

| Score | Examples |
|-------|----------|
| 1 | Pure opinion, no rationale |
| 2 | Some logic: "Good management, growing market" |
| 3 | Full thesis with numbers: "15% EBITDA margin, 3x sales is cheap for SaaS" |

### 3. Risk Awareness (1-3)

Does speaker acknowledge downsides?

| Score | Examples |
|-------|----------|
| 1 | No risks mentioned, pure bull case |
| 2 | Brief caveats: "Of course there are risks" |
| 3 | Explicit bear case: "If growth slows below 10%, multiple compresses" |

### 4. Recency (1-3)

How recent is the statement?

| Score | Timeframe |
|-------|-----------|
| 1 | >6 months ago |
| 2 | 1-6 months ago |
| 3 | <1 month ago |

## Total Score Interpretation

| Total | Label | Meaning |
|-------|-------|---------|
| 10-12 | High | Strong, well-reasoned, recent recommendation |
| 7-9 | Medium | Solid recommendation with some gaps |
| 4-6 | Low | Vague, old, or one-sided |

## Example Scoring

**Quote:** "Carasent är en turnaround-story med låg churn, handlas till 4x sales mot normalt 6-8x för SaaS. Risken är att organisk tillväxt stannar av." - Per Johansson, 2025-11-05

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| Specificity | 2 | Mentions valuation but no exact price target |
| Reasoning | 3 | Full thesis with comparable multiples |
| Risk-awareness | 2 | Mentions one specific risk |
| Recency | 3 | Recent (within last month at analysis time) |
| **Total** | **10** | **High confidence** |
```

**Step 2: Save file and commit**

```bash
git add .claude/skills/analyze-sentiment/references/confidence-scoring.md
git commit -m "feat(skill): add analyze-sentiment confidence scoring"
```

---

## Task 6: Update Alpha SENTIMENT Agent

**Files:**
- Modify: `.claude/skills/alpha/references/agents.md:171-286`

**Step 1: Read current SENTIMENT agent section**

Verify line numbers by reading the file.

**Step 2: Update SENTIMENT agent prompt**

Replace the SENTIMENT agent section (lines 171-286) with:

```markdown
## Agent 2: SENTIMENT

**Purpose**: Analyze mentions in podcasts, Twitter, and YouTube to gauge market sentiment.

**CRITICAL**: This agent MUST call the `analyze-sentiment` skill, not analyze sources directly.

**Input Sources**:
- Calls: `/analyze-sentiment {ticker}`
- Fallback: `data/sentiment/{ticker}-analysis.json` (cached)

**Prompt Template**:

```markdown
## Task: Sentiment Analysis

Du är SENTIMENT-agenten i Alpha-analysen för {company_name} ({ticker}).

### STEG 1: Kolla cache

Kontrollera om det finns en cached sentiment-analys:
- Sökväg: data/sentiment/{ticker}-analysis.json
- Om finns och <7 dagar gammal: använd den (fråga användaren först)
- Om finns och äldre: rapportera och föreslå uppdatering
- Om saknas: kör full analys

### STEG 2: Kör analyze-sentiment (om behövs)

Använd Skill tool för att köra analyze-sentiment:
```
/analyze-sentiment {ticker}
```

### STEG 3: Kritisk granskning

VIKTIGT: Podcast-påståenden är ÅSIKTER, inte fakta!

- Verifiera påståenden mot fundamenta där möjligt
- Flagga motstridiga åsikter mellan talare
- Notera vem som äger aktier (bias-risk)
- Vikta nyare åsikter högre

### STEG 4: Syntes

Sammanfatta från analyze-sentiment output:
- Overall sentiment score
- Notable speakers (med confidence scores)
- Bull/bear arguments (deduplicated)
- Trend (improving/stable/deteriorating)

### Output

Returnera samma schema som analyze-sentiment, men med:
- Din kritiska granskning tillagd i summary
- Eventuella verifierade/falsifierade claims
- Adjusted confidence om du hittat motsägelser
```

**Output Schema**:

```json
{
  "agent": "sentiment",
  "company": "string",
  "ticker": "string",
  "analysis_date": "YYYY-MM-DD",
  "data_source": "cached|fresh_analysis",
  "triage_summary": {
    "sources_reviewed": 0,
    "sources_analyzed": 0,
    "sources_ignored": 0
  },
  "overall_sentiment": {
    "score": 0.0,
    "label": "bullish|neutral|bearish",
    "trend": "improving|stable|deteriorating",
    "confidence": "high|medium|low"
  },
  "notable_speakers": [
    {
      "name": "string",
      "affiliation": "string",
      "stance": "bull|bear|neutral",
      "owns_position": true,
      "argument": "string",
      "quote": "string",
      "source": "string",
      "confidence_score": 0
    }
  ],
  "bull_arguments": ["string"],
  "bear_arguments": ["string"],
  "quotes": [
    {
      "id": "string",
      "text": "string",
      "speaker": "string",
      "confidence_score": {
        "total": 0,
        "label": "high|medium|low"
      }
    }
  ],
  "critical_notes": ["string"],
  "summary": "string"
}
```
```

**Step 3: Save changes**

**Step 4: Commit**

```bash
git add .claude/skills/alpha/references/agents.md
git commit -m "feat(alpha): update SENTIMENT agent to use analyze-sentiment skill"
```

---

## Task 7: Update Alpha FUNDAMENTA Agent

**Files:**
- Modify: `.claude/skills/alpha/references/agents.md:56-167`

**Step 1: Update FUNDAMENTA agent to call analyze-filings**

Add cache-check and skill delegation:

```markdown
## Agent 1: FUNDAMENTA

**Purpose**: Analyze financial reports, CEO letters, and company fundamentals.

**CRITICAL**: This agent MUST check for cached filings analysis first, then call `analyze-filings` if needed.

**Input Sources**:
- Primary: `data/filings/analysis/{company}/*.json` - Cached filings analyses
- Fallback: Call `analyze-filings` skill for PDFs

**Prompt Template**:

```markdown
## Task: Fundamental Analysis

Du är FUNDAMENTA-agenten i Alpha-analysen för {company_name} ({ticker}).

### STEG 1: Kolla cached analys

Sök efter befintliga filings-analyser:
```python
from pathlib import Path
analysis_dir = Path(f'data/filings/analysis/{company_slug}')
if analysis_dir.exists():
    analyses = sorted(analysis_dir.glob('*.json'))
    # Använd senaste
```

Om cached analys finns och är <90 dagar gammal: använd den.

### STEG 2: Kör analyze-filings (om behövs)

Om ingen cached analys finns:
1. Kolla om PDFs finns: `data/filings/raw/{company}/*.pdf`
2. Om ja: Använd Skill tool för `/analyze-filings {company}`
3. Om nej: Rapportera att filings saknas

VIKTIGT: Läs ALDRIG PDFs direkt - delegera till analyze-filings!

### STEG 3: Extrahera nyckeltal

Från filings-analysen, extrahera:
- Revenue: trajectory, CAGR, trend
- Margins: gross, EBIT, net + trends
- Cash flow: FCF, FCF margin, conversion
- Balance sheet: net debt, health
- CEO analysis: tone, credibility, promises
- Red/green flags

### Output

Returnera strukturerad JSON med all fundamenta-data.
```
```

**Step 2: Save and commit**

```bash
git add .claude/skills/alpha/references/agents.md
git commit -m "feat(alpha): update FUNDAMENTA agent to use analyze-filings skill"
```

---

## Task 8: Create Sentiment Data Directory

**Files:**
- Create: `data/sentiment/.gitkeep`

**Step 1: Create directory**

```bash
mkdir -p data/sentiment
touch data/sentiment/.gitkeep
```

**Step 2: Commit**

```bash
git add data/sentiment/.gitkeep
git commit -m "chore: create sentiment data directory"
```

---

## Task 9: Update Alpha Skill Main File

**Files:**
- Modify: `.claude/skills/alpha/SKILL.md`

**Step 1: Add reference to new workflow in SKILL.md**

Add after line 37 in the Reference Files table:

```markdown
| `references/cache-logic.md` | Cache checking for SENTIMENT and FUNDAMENTA |
```

**Step 2: Update Step 4 description**

Update "Step 4: Spawn Parallel Agents" section to mention skill delegation:

```markdown
### Step 4: Spawn Parallel Agents

Launch agents 1-4 simultaneously using Task tool:

| Agent | Calls Skill | Focus |
|-------|-------------|-------|
| FUNDAMENTA | `analyze-filings` (cached) | Revenue, margins, cash flow, CEO credibility |
| SENTIMENT | `analyze-sentiment` (cached) | Market sentiment, notable speakers, triage |
| INSIDER | - | Net direction, significant trades |
| EXTERN | - | News, Reddit, analyst views, short interest |

**Cache Logic**: FUNDAMENTA and SENTIMENT check for cached analyses first.
- If cached and fresh: ask user to use or refresh
- If stale or missing: run respective skill

See: `references/agents.md`
```

**Step 3: Commit**

```bash
git add .claude/skills/alpha/SKILL.md
git commit -m "feat(alpha): document skill delegation and cache logic"
```

---

## Task 10: Create Cache Logic Reference

**Files:**
- Create: `.claude/skills/alpha/references/cache-logic.md`

**Step 1: Write cache logic documentation**

```markdown
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
cache_path = Path(f'data/sentiment/{ticker}-analysis.json')
if cache_path.exists():
    cached = json.loads(cache_path.read_text())
    age = (now - datetime.fromisoformat(cached['analyzed_at'])).days
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
    latest = sorted(analysis_dir.glob('*.json'))[-1]
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
```

**Step 2: Commit**

```bash
git add .claude/skills/alpha/references/cache-logic.md
git commit -m "feat(alpha): add cache logic documentation"
```

---

## Task 11: Final Verification

**Step 1: Verify all files created**

```bash
find .claude/skills/analyze-sentiment -type f | sort
find .claude/skills/alpha/references -name "*.md" | sort
ls data/sentiment/
```

Expected:
```
.claude/skills/analyze-sentiment/SKILL.md
.claude/skills/analyze-sentiment/references/confidence-scoring.md
.claude/skills/analyze-sentiment/references/output-schema.md
.claude/skills/analyze-sentiment/references/triage-rules.md

.claude/skills/alpha/references/agents.md
.claude/skills/alpha/references/cache-logic.md
.claude/skills/alpha/references/data-inventory.md
.claude/skills/alpha/references/output.md
.claude/skills/alpha/references/valuation.md
.claude/skills/alpha/references/workflow.md

data/sentiment/.gitkeep
```

**Step 2: Verify git log**

```bash
git log --oneline -10
```

Expected: 8-10 commits for this feature branch

**Step 3: Run test analysis (manual)**

After implementation, test with:
```
/analyze-sentiment CARA
```

Verify:
- Triage log shows all sources reviewed
- Confidence scores calculated correctly
- Output saved to `data/sentiment/CARA-analysis.json`

---

## Summary

| Task | Files | Purpose |
|------|-------|---------|
| 1 | Directory structure | Scaffold analyze-sentiment skill |
| 2 | SKILL.md | Main workflow documentation |
| 3 | output-schema.md | JSON schema for output |
| 4 | triage-rules.md | Decision matrix for sources |
| 5 | confidence-scoring.md | Quote scoring criteria |
| 6 | agents.md (SENTIMENT) | Delegate to analyze-sentiment |
| 7 | agents.md (FUNDAMENTA) | Delegate to analyze-filings |
| 8 | data/sentiment/ | Storage directory |
| 9 | alpha/SKILL.md | Document new flow |
| 10 | cache-logic.md | Cache checking rules |
| 11 | Verification | Ensure all complete |
