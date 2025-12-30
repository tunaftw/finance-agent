# Alpha Extractor - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a Claude Code skill that aggregates all available data about a company to produce a fair value estimate with Bull/Base/Bear scenarios.

**Architecture:** Orchestrator pattern with 5 parallel agents for data collection, followed by synthesis and valuation. Adaptive execution based on available data.

**Tech Stack:** Python, Claude Code skill (SKILL.md), parallel Task agents, JSON storage, existing PodStock data infrastructure.

**Design Document:** `docs/plans/2025-12-30-alpha-extractor-design.md`

---

## Task 1: Create Skill Skeleton

**Files:**
- Create: `.claude/skills/alpha/SKILL.md`
- Create: `data/bolagsanalys/.gitkeep`

**Step 1: Create skill directory structure**

```bash
mkdir -p .claude/skills/alpha
mkdir -p data/bolagsanalys
touch data/bolagsanalys/.gitkeep
```

**Step 2: Create basic SKILL.md**

Create `.claude/skills/alpha/SKILL.md` with frontmatter and overview:

```markdown
---
name: alpha
description: Aggregera all tillgänglig data om ett bolag för att beräkna fair value med Bull/Base/Bear scenarios. Brutalt objektiv - fokuserar på pris vs värde.
---

# Alpha Extractor

Sammanställ ALL tillgänglig data om ett bolag och beräkna ett motiverat fair value.

## Quick Start

Invokera med bolagsnamn eller ticker + valfri kontext:

```
/alpha Betsson "överväger att öka position"
/alpha EVO "har i portfölj, vill uppdatera"
/alpha INVE-B "nytt case, känner inte bolaget"
```

## Kärnprinciper

- **Objektiv, inte yes-sayer** - aktivt leta efter bear-case och risker
- **Pris är allt** - fantastiskt bolag till fel pris = dålig investering
- **Konsekvent metodik** - samma ramverk oavsett bransch
- **Ärlig om begränsningar** - flagga saknad data, tvinga inte fram slutsatser

## Implementation

Se `references/workflow.md` för fullständig implementation.
```

**Step 3: Commit skeleton**

```bash
git add .claude/skills/alpha/ data/bolagsanalys/
git commit -m "feat(alpha): add skill skeleton and data directory"
```

---

## Task 2: Create Data Inventory Module

**Files:**
- Create: `.claude/skills/alpha/references/data-inventory.md`

**Step 1: Create data inventory reference**

Create `.claude/skills/alpha/references/data-inventory.md`:

```markdown
# Data Inventory

## Inventory Function

Kör denna kod för att inventera tillgänglig data om ett bolag:

```python
import json
from pathlib import Path
from datetime import datetime

def inventory_company_data(company_query: str) -> dict:
    """
    Inventera all tillgänglig data för ett bolag.

    Args:
        company_query: Bolagsnamn eller ticker (t.ex. "Betsson", "BETS", "EVO.ST")

    Returns:
        Dict med alla datakällor och deras innehåll
    """
    # Normalisera query för sökning
    query_lower = company_query.lower()
    query_variants = [
        query_lower,
        query_lower.replace('.st', ''),
        query_lower.replace('-', ''),
    ]

    inventory = {
        "query": company_query,
        "timestamp": datetime.now().isoformat(),
        "sources": {}
    }

    # 1. Finansiella rapporter
    filings_dir = Path("data/filings")
    if filings_dir.exists():
        filings = []
        for company_dir in filings_dir.iterdir():
            if company_dir.is_dir() and any(v in company_dir.name.lower() for v in query_variants):
                for f in company_dir.glob("*.json"):
                    filings.append(str(f))
        inventory["sources"]["filings"] = {
            "count": len(filings),
            "files": filings
        }

    # 2. Podcast-omnämningar (sök i analyses)
    podcast_analyses = Path("data/podcasts/analyses-v2")
    if not podcast_analyses.exists():
        podcast_analyses = Path("data/podcasts/analyses")

    if podcast_analyses.exists():
        mentions = []
        for f in podcast_analyses.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                recs = data.get("recommendations", [])
                for rec in recs:
                    stock = rec.get("stock_name", "").lower()
                    ticker = rec.get("ticker", "").lower()
                    if any(v in stock or v in ticker for v in query_variants):
                        mentions.append({
                            "file": str(f),
                            "episode_id": data.get("episode_id"),
                            "date": data.get("date"),
                            "action": rec.get("action"),
                            "speaker": rec.get("speaker")
                        })
            except:
                pass
        inventory["sources"]["podcasts"] = {
            "count": len(mentions),
            "mentions": mentions
        }

    # 3. Twitter-omnämningar
    twitter_analyses = Path("data/twitter/analyses")
    if twitter_analyses.exists():
        twitter_mentions = []
        for f in twitter_analyses.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                # Sök i recommendations eller tweets
                if isinstance(data, list):
                    items = data
                else:
                    items = data.get("recommendations", []) + data.get("tweets", [])
                for item in items:
                    text = str(item).lower()
                    if any(v in text for v in query_variants):
                        twitter_mentions.append({
                            "file": str(f),
                            "handle": f.stem.replace("-analysis", "")
                        })
                        break
            except:
                pass
        inventory["sources"]["twitter"] = {
            "count": len(twitter_mentions),
            "files": [m["file"] for m in twitter_mentions]
        }

    # 4. YouTube-omnämningar
    youtube_analyses = Path("data/youtube/analyses")
    if youtube_analyses.exists():
        youtube_mentions = []
        for f in youtube_analyses.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                recs = data.get("recommendations", [])
                for rec in recs:
                    stock = rec.get("stock_name", "").lower()
                    ticker = rec.get("ticker", "").lower()
                    if any(v in stock or v in ticker for v in query_variants):
                        youtube_mentions.append({
                            "file": str(f),
                            "video_id": data.get("video_id"),
                            "date": data.get("date")
                        })
            except:
                pass
        inventory["sources"]["youtube"] = {
            "count": len(youtube_mentions),
            "mentions": youtube_mentions
        }

    # 5. Insiderdata
    insider_dir = Path("data/insider")
    if insider_dir.exists():
        insider_files = []
        for market_dir in insider_dir.iterdir():
            if market_dir.is_dir():
                for f in market_dir.glob("*.json"):
                    if any(v in f.stem.lower() for v in query_variants):
                        insider_files.append(str(f))
        inventory["sources"]["insider"] = {
            "count": len(insider_files),
            "files": insider_files
        }

    # 6. Nyheter
    news_dir = Path("data/news")
    if news_dir.exists():
        news_files = []
        for company_dir in news_dir.iterdir():
            if company_dir.is_dir() and any(v in company_dir.name.lower() for v in query_variants):
                for f in company_dir.glob("*.json"):
                    news_files.append(str(f))
        inventory["sources"]["news"] = {
            "count": len(news_files),
            "files": news_files
        }

    # 7. Prishistorik
    prices_dir = Path("data/prices")
    if prices_dir.exists():
        price_files = []
        for f in prices_dir.glob("*.json"):
            if any(v in f.stem.lower() for v in query_variants):
                price_files.append(str(f))
        inventory["sources"]["prices"] = {
            "count": len(price_files),
            "files": price_files
        }

    # 8. Databas (SQLite)
    db_path = Path("data/podstock.db")
    inventory["sources"]["database"] = {
        "available": db_path.exists(),
        "path": str(db_path) if db_path.exists() else None
    }

    # Sammanfattning
    total_sources = sum(
        s.get("count", 0) for s in inventory["sources"].values()
        if isinstance(s, dict) and "count" in s
    )
    inventory["summary"] = {
        "total_data_points": total_sources,
        "mode": "full" if total_sources >= 10 else "partial" if total_sources > 0 else "discovery"
    }

    return inventory

# Kör och visa resultat
if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "Betsson"
    result = inventory_company_data(query)
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

## Visa inventering

Efter att ha kört inventory_company_data(), visa resultatet:

```
📊 DATAINVENTERING: {company}
{'=' * 50}

Läge: {mode}

| Källa | Antal | Status |
|-------|-------|--------|
| Finansiella rapporter | {filings} | ✓/○ |
| Podcast-mentions | {podcasts} | ✓/○ |
| Twitter-mentions | {twitter} | ✓/○ |
| YouTube-mentions | {youtube} | ✓/○ |
| Insiderdata | {insider} | ✓/○ |
| Nyheter | {news} | ✓/○ |
| Prishistorik | {prices} | ✓/○ |
| Databas | {db} | ✓/○ |

{'=' * 50}
```
```

**Step 2: Commit data inventory**

```bash
git add .claude/skills/alpha/references/
git commit -m "feat(alpha): add data inventory module"
```

---

## Task 3: Create Agent Definitions

**Files:**
- Create: `.claude/skills/alpha/references/agents.md`

**Step 1: Create agents reference**

Create `.claude/skills/alpha/references/agents.md`:

```markdown
# Agent Definitions

## Orchestrator Flow

```
User: /alpha BETS "överväger ökning"
         │
         ▼
    ORCHESTRATOR
         │
         ├──► Run data inventory
         │
         ├──► Spawn agents in parallel (based on available data)
         │
         ├──► Collect agent results
         │
         └──► Run synthesis & valuation
```

## Agent 1: FUNDAMENTA

**Syfte:** Analysera finansiella rapporter och VD-ord

**Input:**
- Lista av filings från inventory
- Bolagsnamn och kontext

**Prompt:**
```
Du är en fundamental analytiker. Analysera följande finansiella data för {company}:

RAPPORTER:
{filings_content}

Extrahera:
1. Nyckeltal över tid (omsättning, EBITDA, nettoresultat, FCF)
2. Marginaler och trender
3. VD-ord analys:
   - Tonfall (optimistiskt/realistiskt/defensivt)
   - Löften som getts
   - Måluppfyllnad (levererar de vad de säger?)
4. Balansräkning (skuldsättning, kassa, rörelsekapital)
5. Cyklikalitet (är bolaget cykliskt?)

Output JSON:
{
  "revenue_cagr_3y": "X%",
  "ebitda_margin_current": "X%",
  "ebitda_margin_trend": "improving/stable/declining",
  "fcf_yield": "X%",
  "net_debt_ebitda": X.X,
  "ceo_tone": "optimistic/realistic/defensive",
  "promise_delivery": "exceeds/meets/misses",
  "cyclicality": "high/medium/low",
  "key_metrics": [...],
  "concerns": [...],
  "positives": [...]
}
```

## Agent 2: SENTIMENT

**Syfte:** Analysera podcast, Twitter, YouTube mentions

**Input:**
- Lista av mentions från inventory
- Prishistorik för kontext

**Prompt:**
```
Du analyserar sentiment kring {company} från finansiella influencers.

OMNÄMNINGAR:
{mentions_content}

PRISHISTORIK:
{price_context}

Analysera:
1. Övergripande sentiment (bullish/bearish/neutral)
2. Trender över tid (ökar/minskar intresset?)
3. Vem pratar om bolaget? (profiler)
4. Vanligaste argumenten (bull och bear)
5. Historisk träffsäkerhet:
   - När nämndes bolaget tidigare?
   - Vad var kursen då?
   - Hur gick det efteråt?

Output JSON:
{
  "overall_sentiment": "bullish/neutral/bearish",
  "sentiment_trend": "increasing/stable/decreasing",
  "mention_count": X,
  "notable_speakers": [...],
  "bull_arguments": [...],
  "bear_arguments": [...],
  "historical_calls": [
    {"date": "YYYY-MM-DD", "price_then": X, "action": "buy", "price_now": Y, "return": "X%"}
  ]
}
```

## Agent 3: INSIDER & ÄGARE

**Syfte:** Analysera insynshandel och ägarstruktur

**Input:**
- Insiderdata från inventory
- Aktuell kurs

**Prompt:**
```
Du analyserar insynshandel för {company}.

INSYNSTRANSAKTIONER:
{insider_data}

AKTUELL KURS: {current_price}

Analysera:
1. Nettoriktning (köp/sälj/neutralt)
2. Signifikanta transaktioner (VD, styrelse, storägare)
3. Priskontext (kurs vid transaktion vs nu)
4. Mönster (köper de vid dippar?)

Output JSON:
{
  "net_direction": "buying/selling/neutral",
  "significant_transactions": [
    {"who": "VD", "action": "buy", "amount_sek": X, "price_then": Y, "price_now": Z}
  ],
  "signal_strength": "strong/moderate/weak",
  "interpretation": "..."
}
```

## Agent 4: EXTERN RESEARCH

**Syfte:** Söka extern information

**Input:**
- Bolagsnamn
- Kontext från användaren

**Verktyg:**
- WebSearch
- WebFetch

**Prompt:**
```
Du gör extern research på {company}.

Sök efter:
1. Senaste nyheter (Google News)
2. Reddit-diskussioner (r/stocks, r/investing, svenska subreddits)
3. Placera forum/artiklar
4. Blankarrapporter eller kritik
5. Bolagets IR-sida

Fokusera EXTRA på:
- Negativ information (motvikt till bull-case)
- Risker som inte syns i rapporter
- Konkurrenssituation

Output JSON:
{
  "news_summary": "...",
  "reddit_sentiment": "...",
  "short_reports": [...],
  "risks_found": [...],
  "notable_findings": [...],
  "sources": [{"url": "...", "summary": "..."}]
}
```

## Agent 5: RISKER & BEAR CASE

**Syfte:** Aktivt leta motargument och risker

**Input:**
- Alla andra agenters output
- Bolagskontext

**Prompt:**
```
Du är djävulens advokat. Din uppgift är att hitta ALLA anledningar att INTE investera i {company}.

FUNDAMENTAL DATA:
{fundamenta_output}

SENTIMENT:
{sentiment_output}

INSIDER:
{insider_output}

EXTERN RESEARCH:
{external_output}

Identifiera:
1. Största riskerna (sannolikhet + påverkan)
2. Vad kan gå fel som inte diskuterats?
3. Historiska paralleller (liknande bolag/situationer som gått dåligt)
4. Varningsflaggor i data
5. Bear-case scenario (vad händer om allt går fel?)

Output JSON:
{
  "top_risks": [
    {"risk": "...", "probability": "high/medium/low", "impact": "high/medium/low", "reasoning": "..."}
  ],
  "warning_flags": [...],
  "historical_parallels": [...],
  "bear_case_narrative": "...",
  "worst_case_downside": "-X%"
}
```

## Synthesis Prompt

**Input:** Alla 5 agenters output

**Prompt:**
```
Du ska nu syntetisera all data till en slutlig värdering av {company}.

FUNDAMENTA:
{agent1_output}

SENTIMENT:
{agent2_output}

INSIDER:
{agent3_output}

EXTERN RESEARCH:
{agent4_output}

RISKER:
{agent5_output}

ANVÄNDARKONTEXT: {user_context}

Skapa:

1. BOLAGSKLASSIFICERING
   - Typ (bank/gaming/SaaS/industri/fastighet/konsument)
   - Relevanta multiplar

2. PEER-FÖRSLAG
   - 3-5 jämförbara bolag
   - Motivering

3. KVALITATIV JUSTERING
   - Tillväxt vs peers
   - Marginaltrend
   - Balansräkning
   - Moat
   - Management
   - Risker

4. SCENARIOMODELL

   BULL ({bull_prob}%):
   - Antaganden
   - Multipel
   - Fair value: X SEK

   BASE ({base_prob}%):
   - Antaganden
   - Multipel
   - Fair value: X SEK

   BEAR ({bear_prob}%):
   - Antaganden
   - Multipel
   - Fair value: X SEK

5. VIKTAT FAIR VALUE
   = bull_prob × bull_fv + base_prob × base_fv + bear_prob × bear_fv

6. VERDICT
   - Fair value vs aktuell kurs
   - Uppsida/nedsida
   - Confidence (hög/medium/låg)
   - Rekommendation
```
```

**Step 2: Commit agents**

```bash
git add .claude/skills/alpha/references/agents.md
git commit -m "feat(alpha): add agent definitions"
```

---

## Task 4: Create Valuation Module

**Files:**
- Create: `.claude/skills/alpha/references/valuation.md`

**Step 1: Create valuation reference**

Create `.claude/skills/alpha/references/valuation.md`:

```markdown
# Valuation Module

## Bolagsklassificering

| Typ | Kännetecken | Primära multiplar |
|-----|-------------|-------------------|
| Bank/Finans | Reglerad, räntenetto | P/B, P/E, ROE |
| Gaming/Betting | Höga marginaler, regulatorisk risk | EV/EBITDA, P/E, FCF yield |
| SaaS/Tech | Recurring revenue, hög tillväxt | EV/Sales, Rule of 40, ARR |
| Industri/Cyklisk | Capex-tung, cyklisk | EV/EBITDA (normaliserad), ROIC |
| Fastighet | Tillgångstung | P/NAV, FFO yield, LTV |
| Konsument | Varumärke, marginaler | P/E, EV/EBIT |

**Alltid med:** FCF yield, Nettoskuld/EBITDA

## Multipel-beräkning

```python
def calculate_multiples(financials: dict, market_cap: float, net_debt: float) -> dict:
    """Beräkna relevanta multiplar."""
    ev = market_cap + net_debt

    return {
        "p_e": market_cap / financials["net_income"] if financials["net_income"] > 0 else None,
        "ev_ebitda": ev / financials["ebitda"] if financials["ebitda"] > 0 else None,
        "ev_sales": ev / financials["revenue"],
        "p_fcf": market_cap / financials["fcf"] if financials["fcf"] > 0 else None,
        "fcf_yield": (financials["fcf"] / market_cap * 100) if financials["fcf"] > 0 else None,
        "net_debt_ebitda": net_debt / financials["ebitda"] if financials["ebitda"] > 0 else None,
    }
```

## Fair Value Beräkning

```python
def calculate_fair_value(
    scenarios: list[dict],
    shares_outstanding: float
) -> dict:
    """
    Beräkna viktat fair value från scenarios.

    Args:
        scenarios: [
            {"name": "bull", "probability": 0.25, "ev": 50000, "net_debt": 5000},
            {"name": "base", "probability": 0.55, "ev": 40000, "net_debt": 5000},
            {"name": "bear", "probability": 0.20, "ev": 25000, "net_debt": 5000},
        ]
        shares_outstanding: Antal aktier

    Returns:
        {"weighted_fair_value": X, "scenarios": [...]}
    """
    result = {"scenarios": []}
    weighted_sum = 0

    for s in scenarios:
        equity_value = s["ev"] - s["net_debt"]
        fair_value_per_share = equity_value / shares_outstanding

        result["scenarios"].append({
            "name": s["name"],
            "probability": s["probability"],
            "fair_value": fair_value_per_share
        })

        weighted_sum += s["probability"] * fair_value_per_share

    result["weighted_fair_value"] = round(weighted_sum, 2)
    return result
```

## Scenario Builder

```python
def build_scenarios(
    base_ebitda: float,
    base_multiple: float,
    net_debt: float,
    shares: float,
    bull_adjustment: dict = None,
    bear_adjustment: dict = None
) -> list[dict]:
    """
    Bygg Bull/Base/Bear scenarios.

    Defaults:
    - Bull: +20% EBITDA, +1x multipel
    - Bear: -20% EBITDA, -1.5x multipel
    """
    bull_adj = bull_adjustment or {"ebitda_delta": 0.20, "multiple_delta": 1.0}
    bear_adj = bear_adjustment or {"ebitda_delta": -0.20, "multiple_delta": -1.5}

    return [
        {
            "name": "bull",
            "probability": 0.25,
            "ebitda": base_ebitda * (1 + bull_adj["ebitda_delta"]),
            "multiple": base_multiple + bull_adj["multiple_delta"],
            "ev": base_ebitda * (1 + bull_adj["ebitda_delta"]) * (base_multiple + bull_adj["multiple_delta"]),
            "net_debt": net_debt
        },
        {
            "name": "base",
            "probability": 0.55,
            "ebitda": base_ebitda,
            "multiple": base_multiple,
            "ev": base_ebitda * base_multiple,
            "net_debt": net_debt
        },
        {
            "name": "bear",
            "probability": 0.20,
            "ebitda": base_ebitda * (1 + bear_adj["ebitda_delta"]),
            "multiple": base_multiple + bear_adj["multiple_delta"],
            "ev": base_ebitda * (1 + bear_adj["ebitda_delta"]) * (base_multiple + bear_adj["multiple_delta"]),
            "net_debt": net_debt
        }
    ]
```

## Verdict Generator

```python
def generate_verdict(
    weighted_fv: float,
    current_price: float,
    confidence: str,
    scenarios: list[dict],
    key_risks: list[str]
) -> dict:
    """Generera verdict baserat på fair value vs pris."""

    upside = (weighted_fv - current_price) / current_price * 100

    if upside > 20:
        verdict = "KÖPVÄRD"
    elif upside > 5:
        verdict = "ATTRAKTIV"
    elif upside > -10:
        verdict = "FAIR VÄRDERAD"
    elif upside > -20:
        verdict = "FULLVÄRDERAD"
    else:
        verdict = "ÖVERVÄRDERAD"

    bear_fv = next(s["fair_value"] for s in scenarios if s["name"] == "bear")
    bear_downside = (bear_fv - current_price) / current_price * 100

    return {
        "verdict": verdict,
        "weighted_fair_value": weighted_fv,
        "current_price": current_price,
        "upside_pct": round(upside, 1),
        "bear_downside_pct": round(bear_downside, 1),
        "confidence": confidence,
        "key_risks": key_risks
    }
```
```

**Step 2: Commit valuation module**

```bash
git add .claude/skills/alpha/references/valuation.md
git commit -m "feat(alpha): add valuation module"
```

---

## Task 5: Create Output & Storage Module

**Files:**
- Create: `.claude/skills/alpha/references/output.md`

**Step 1: Create output reference**

Create `.claude/skills/alpha/references/output.md`:

```markdown
# Output & Storage

## Analysis JSON Schema

Analyser sparas till: `data/bolagsanalys/{ticker}/{YYYY-MM-DD}-analysis.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["ticker", "company", "date", "weighted_fair_value", "current_price", "verdict"],
  "properties": {
    "ticker": {"type": "string"},
    "company": {"type": "string"},
    "date": {"type": "string", "format": "date"},
    "context": {"type": "string"},

    "data_sources": {
      "type": "object",
      "properties": {
        "filings": {"type": "integer"},
        "podcasts": {"type": "integer"},
        "twitter": {"type": "integer"},
        "youtube": {"type": "integer"},
        "insider": {"type": "integer"},
        "news": {"type": "integer"},
        "external_search": {"type": "boolean"}
      }
    },

    "fundamenta": {
      "type": "object",
      "properties": {
        "revenue_cagr_3y": {"type": "string"},
        "ebitda_margin": {"type": "string"},
        "fcf_yield": {"type": "string"},
        "net_debt_ebitda": {"type": "number"},
        "ceo_tone": {"type": "string"},
        "promise_delivery": {"type": "string"}
      }
    },

    "sentiment": {
      "type": "object",
      "properties": {
        "overall": {"type": "string", "enum": ["bullish", "neutral", "bearish"]},
        "trend": {"type": "string"},
        "mention_count": {"type": "integer"},
        "notable_speakers": {"type": "array", "items": {"type": "string"}},
        "bull_arguments": {"type": "array", "items": {"type": "string"}},
        "bear_arguments": {"type": "array", "items": {"type": "string"}}
      }
    },

    "insider": {
      "type": "object",
      "properties": {
        "net_direction": {"type": "string", "enum": ["buying", "selling", "neutral"]},
        "signal_strength": {"type": "string"},
        "significant_transactions": {"type": "array"}
      }
    },

    "risks": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "risk": {"type": "string"},
          "probability": {"type": "string"},
          "impact": {"type": "string"}
        }
      }
    },

    "peers": {
      "type": "object",
      "properties": {
        "selected": {"type": "array", "items": {"type": "string"}},
        "company_multiple": {"type": "number"},
        "peer_average": {"type": "number"},
        "discount_vs_peers": {"type": "string"}
      }
    },

    "scenarios": {
      "type": "object",
      "properties": {
        "bull": {
          "type": "object",
          "properties": {
            "probability": {"type": "number"},
            "fair_value": {"type": "number"},
            "assumptions": {"type": "array", "items": {"type": "string"}}
          }
        },
        "base": {"$ref": "#/properties/scenarios/properties/bull"},
        "bear": {"$ref": "#/properties/scenarios/properties/bull"}
      }
    },

    "weighted_fair_value": {"type": "number"},
    "current_price": {"type": "number"},
    "verdict": {"type": "string"},
    "upside": {"type": "string"},
    "confidence": {"type": "string", "enum": ["HÖG", "MEDIUM", "LÅG"]},
    "recommendation": {"type": "string"}
  }
}
```

## Save Analysis

```python
import json
from pathlib import Path
from datetime import datetime

def save_analysis(analysis: dict) -> Path:
    """
    Spara analys till fil.

    Returns:
        Path till sparad fil
    """
    ticker = analysis["ticker"].upper()
    date = analysis.get("date", datetime.now().strftime("%Y-%m-%d"))

    # Skapa katalog
    output_dir = Path(f"data/bolagsanalys/{ticker}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Spara
    output_file = output_dir / f"{date}-analysis.json"
    output_file.write_text(json.dumps(analysis, indent=2, ensure_ascii=False))

    return output_file
```

## Display Functions

### Interaktiv Header

```python
def display_header(company: str, inventory: dict):
    mode = inventory["summary"]["mode"]
    mode_emoji = {"full": "🟢", "partial": "🟡", "discovery": "🔴"}[mode]

    print(f"""
{'=' * 60}
ALPHA EXTRACTOR: {company}
{'=' * 60}

{mode_emoji} Läge: {mode.upper()}

📊 Datainventering:
""")

    sources = inventory["sources"]
    for name, data in sources.items():
        if isinstance(data, dict) and "count" in data:
            emoji = "✓" if data["count"] > 0 else "○"
            print(f"  {emoji} {name}: {data['count']} st")
```

### Verdict Display

```python
def display_verdict(result: dict):
    verdict = result["verdict"]
    fv = result["weighted_fair_value"]
    price = result["current_price"]
    upside = result["upside"]
    confidence = result["confidence"]

    verdict_colors = {
        "KÖPVÄRD": "🟢",
        "ATTRAKTIV": "🟢",
        "FAIR VÄRDERAD": "🟡",
        "FULLVÄRDERAD": "🟠",
        "ÖVERVÄRDERAD": "🔴"
    }

    print(f"""
{'=' * 60}
VERDICT
{'=' * 60}

Fair Value (viktat): {fv} SEK
Aktuell kurs: {price} SEK
Uppsida: {upside}

{verdict_colors.get(verdict, "⚪")} BEDÖMNING: {verdict}

Confidence: {confidence}
""")

    if result.get("key_risks"):
        print("\nMEN TÄNK PÅ:")
        for risk in result["key_risks"][:3]:
            print(f"  ├─ {risk}")

    if result.get("recommendation"):
        print(f"\n💡 {result['recommendation']}")
```
```

**Step 2: Commit output module**

```bash
git add .claude/skills/alpha/references/output.md
git commit -m "feat(alpha): add output and storage module"
```

---

## Task 6: Create Main Workflow

**Files:**
- Create: `.claude/skills/alpha/references/workflow.md`
- Update: `.claude/skills/alpha/SKILL.md`

**Step 1: Create workflow reference**

Create `.claude/skills/alpha/references/workflow.md`:

```markdown
# Main Workflow

## Full Implementation

När `/alpha {bolag} "{kontext}"` invokeras:

### Step 1: Parse Input

```python
import re

def parse_alpha_input(args: str) -> dict:
    """
    Parse input till company och kontext.

    Exempel:
        "BETS överväger ökning" -> {"company": "BETS", "context": "överväger ökning"}
        "Betsson" -> {"company": "Betsson", "context": None}
    """
    # Matcha: TICKER/Namn "kontext" eller bara TICKER/Namn
    match = re.match(r'^([A-Za-zÅÄÖåäö0-9.-]+)\s*(?:"([^"]+)")?(.*)$', args.strip())

    if match:
        company = match.group(1)
        context = match.group(2) or match.group(3).strip() or None
        return {"company": company, "context": context}

    return {"company": args.strip(), "context": None}
```

### Step 2: Run Data Inventory

```python
# Se references/data-inventory.md
inventory = inventory_company_data(company)
display_header(company, inventory)
```

### Step 3: Handle Missing Data

```python
mode = inventory["summary"]["mode"]

if mode == "discovery":
    print(f"""
⚠️  DISCOVERY MODE

Ingen lokal data hittades för {company}.
Kör primärt extern sökning för att bygga grundbild.

Fortsätta? (y/n)
""")
    # Vänta på bekräftelse via AskUserQuestion

elif mode == "partial":
    missing = []
    for source, data in inventory["sources"].items():
        if isinstance(data, dict) and data.get("count", 0) == 0:
            missing.append(source)

    print(f"""
⚠️  PARTIELL DATA

Saknar: {', '.join(missing)}

Analysen körs med tillgänglig data.
Extern sökning viktas upp för att kompensera.
""")
```

### Step 4: Spawn Agents (Parallel)

```python
# Använd Task tool för att spawna agenter parallellt

agents_to_run = []

# Agent 1: Fundamenta (om filings finns)
if inventory["sources"].get("filings", {}).get("count", 0) > 0:
    agents_to_run.append({
        "name": "fundamenta",
        "prompt": FUNDAMENTA_PROMPT.format(
            company=company,
            filings_content=load_filings(inventory["sources"]["filings"]["files"])
        )
    })

# Agent 2: Sentiment (om mentions finns)
sentiment_count = sum([
    inventory["sources"].get("podcasts", {}).get("count", 0),
    inventory["sources"].get("twitter", {}).get("count", 0),
    inventory["sources"].get("youtube", {}).get("count", 0),
])
if sentiment_count > 0:
    agents_to_run.append({
        "name": "sentiment",
        "prompt": SENTIMENT_PROMPT.format(
            company=company,
            mentions_content=load_mentions(inventory)
        )
    })

# Agent 3: Insider (om insider finns)
if inventory["sources"].get("insider", {}).get("count", 0) > 0:
    agents_to_run.append({
        "name": "insider",
        "prompt": INSIDER_PROMPT.format(
            company=company,
            insider_data=load_insider(inventory)
        )
    })

# Agent 4: Extern (alltid)
agents_to_run.append({
    "name": "external",
    "prompt": EXTERNAL_PROMPT.format(company=company)
})

# Agent 5: Risker (körs efter de andra)
# Väntar på input från andra agenter
```

### Step 5: Collect Results

```python
# Samla resultat från alla agenter
results = {
    "fundamenta": agent1_result,
    "sentiment": agent2_result,
    "insider": agent3_result,
    "external": agent4_result,
}
```

### Step 6: Run Risk Agent

```python
# Agent 5 får input från alla andra
risk_result = run_risk_agent(
    company=company,
    fundamenta=results.get("fundamenta"),
    sentiment=results.get("sentiment"),
    insider=results.get("insider"),
    external=results.get("external")
)
results["risks"] = risk_result
```

### Step 7: Suggest Peers

```python
# Baserat på bolagstyp, föreslå peers
company_type = determine_company_type(results["fundamenta"])
suggested_peers = suggest_peers(company, company_type)

print(f"""
PEER-FÖRSLAG

Bolagstyp: {company_type}
Föreslagna peers: {', '.join(suggested_peers)}

Godkänn eller justera? (Enter för godkänn, eller ange egna)
""")
# AskUserQuestion för bekräftelse
```

### Step 8: Build Scenarios

```python
# Se references/valuation.md
scenarios = build_scenarios(
    base_ebitda=results["fundamenta"]["ebitda"],
    base_multiple=peer_average_multiple,
    net_debt=results["fundamenta"]["net_debt"],
    shares=shares_outstanding
)

# Justera sannolikheter baserat på data
adjusted_scenarios = adjust_probabilities(
    scenarios=scenarios,
    sentiment=results["sentiment"],
    insider=results["insider"],
    risks=results["risks"]
)

print(f"""
SCENARIOMODELL

|       | Bull ({adjusted_scenarios[0]['probability']*100:.0f}%) | Base ({adjusted_scenarios[1]['probability']*100:.0f}%) | Bear ({adjusted_scenarios[2]['probability']*100:.0f}%) |
|-------|------|------|------|
| EBITDA | {adjusted_scenarios[0]['ebitda']} | {adjusted_scenarios[1]['ebitda']} | {adjusted_scenarios[2]['ebitda']} |
| Multipel | {adjusted_scenarios[0]['multiple']}x | {adjusted_scenarios[1]['multiple']}x | {adjusted_scenarios[2]['multiple']}x |
| Fair Value | {adjusted_scenarios[0]['fair_value']} SEK | {adjusted_scenarios[1]['fair_value']} SEK | {adjusted_scenarios[2]['fair_value']} SEK |

Justera sannolikheter? (Enter för godkänn)
""")
```

### Step 9: Calculate Fair Value

```python
fair_value_result = calculate_fair_value(adjusted_scenarios, shares_outstanding)
weighted_fv = fair_value_result["weighted_fair_value"]
```

### Step 10: Generate Verdict

```python
verdict = generate_verdict(
    weighted_fv=weighted_fv,
    current_price=current_price,
    confidence=determine_confidence(inventory, results),
    scenarios=fair_value_result["scenarios"],
    key_risks=results["risks"]["top_risks"][:3]
)

display_verdict(verdict)
```

### Step 11: Save Analysis

```python
analysis = compile_full_analysis(
    company=company,
    context=context,
    inventory=inventory,
    results=results,
    scenarios=adjusted_scenarios,
    verdict=verdict
)

output_path = save_analysis(analysis)
print(f"\n💾 Analys sparad: {output_path}")
```

## Interactive Follow-ups

Efter varje sektion, tillåt följdfrågor:

```
Följdfråga? (Enter för att fortsätta)
> Hur har marginalen utvecklats?

[Svara baserat på data]

Följdfråga? (Enter för att fortsätta)
>
[Fortsätt till nästa sektion]
```
```

**Step 2: Update main SKILL.md**

Uppdatera `.claude/skills/alpha/SKILL.md` med komplett implementation:

```markdown
---
name: alpha
description: Aggregera all tillgänglig data om ett bolag för att beräkna fair value med Bull/Base/Bear scenarios. Brutalt objektiv - fokuserar på pris vs värde.
---

# Alpha Extractor

Sammanställ ALL tillgänglig data om ett bolag och beräkna ett motiverat fair value.

## Quick Start

```
/alpha Betsson "överväger att öka position"
/alpha EVO "har i portfölj, vill uppdatera"
/alpha INVE-B "nytt case, känner inte bolaget"
```

## Kärnprinciper

- **Objektiv, inte yes-sayer** - aktivt leta efter bear-case och risker
- **Pris är allt** - fantastiskt bolag till fel pris = dålig investering
- **Konsekvent metodik** - samma ramverk oavsett bransch
- **Ärlig om begränsningar** - flagga saknad data

## Implementation

### Step 1: Parse & Inventory

1. Parse bolagsnamn och kontext från input
2. Kör datainventering (se `references/data-inventory.md`)
3. Visa inventering och läge (full/partial/discovery)

### Step 2: Spawn Agents

Kör parallella agenter baserat på tillgänglig data (se `references/agents.md`):

| Agent | Körs om | Data |
|-------|---------|------|
| FUNDAMENTA | filings > 0 | Rapporter, VD-ord |
| SENTIMENT | mentions > 0 | Podcasts, Twitter, YouTube |
| INSIDER | insider > 0 | Insynsköp/-sälj |
| EXTERN | alltid | WebSearch, WebFetch |
| RISKER | alltid | Output från övriga |

**Parallell execution:**
```
Använd Task tool med run_in_background=true för Agent 1-4
Vänta på alla med TaskOutput
Kör sedan Agent 5 (Risker) med input från övriga
```

### Step 3: Peer Selection

1. Bestäm bolagstyp (bank/gaming/SaaS/industri/fastighet/konsument)
2. Föreslå 3-5 peers
3. Fråga användaren: "Godkänn eller justera peers?"

### Step 4: Valuation

1. Beräkna relevanta multiplar (se `references/valuation.md`)
2. Bygg Bull/Base/Bear scenarios
3. Föreslå sannolikheter baserat på data
4. Fråga användaren: "Justera sannolikheter?"
5. Beräkna viktat fair value

### Step 5: Verdict & Save

1. Generera verdict (KÖPVÄRD/ATTRAKTIV/FAIR/FULLVÄRDERAD/ÖVERVÄRDERAD)
2. Visa key risks
3. Spara till `data/bolagsanalys/{ticker}/{date}-analysis.json`

## References

- `references/data-inventory.md` - Datainventering
- `references/agents.md` - Agentdefinitioner
- `references/valuation.md` - Värderingsmodul
- `references/output.md` - Output & lagring
- `references/workflow.md` - Fullständigt flöde
```

**Step 3: Commit workflow**

```bash
git add .claude/skills/alpha/
git commit -m "feat(alpha): complete skill implementation with workflow"
```

---

## Task 7: Test the Skill

**Step 1: Manual test**

Testa skillen manuellt:

```
/alpha Betsson "test av ny skill"
```

**Step 2: Verify output**

Kontrollera att:
1. Datainventering körs
2. Rätt läge (full/partial/discovery) identifieras
3. Agenter spawnas korrekt
4. Peer-förslag visas
5. Scenarios byggs
6. Verdict genereras
7. Fil sparas till rätt plats

**Step 3: Fix issues**

Om något inte fungerar, identifiera och fixa.

---

## Task 8: Final Commit

**Step 1: Final review**

Granska alla filer i `.claude/skills/alpha/`

**Step 2: Create summary commit**

```bash
git add .
git commit -m "feat(alpha): Alpha Extractor skill complete

Implements company analysis skill that:
- Aggregates all available data sources
- Runs parallel agents for deep analysis
- Calculates fair value with Bull/Base/Bear scenarios
- Provides objective verdict with key risks

Design doc: docs/plans/2025-12-30-alpha-extractor-design.md"
```

---

## Summary

| Task | Beskrivning | Filer |
|------|-------------|-------|
| 1 | Skill skeleton | `SKILL.md`, `data/bolagsanalys/` |
| 2 | Data inventory | `references/data-inventory.md` |
| 3 | Agent definitions | `references/agents.md` |
| 4 | Valuation module | `references/valuation.md` |
| 5 | Output & storage | `references/output.md` |
| 6 | Main workflow | `references/workflow.md`, update `SKILL.md` |
| 7 | Test skill | Manual testing |
| 8 | Final commit | Summary commit |

**Total commits:** 7
**Estimated tasks:** 8
