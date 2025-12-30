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

---

## Reference Files

| File | Purpose |
|------|---------|
| `references/workflow.md` | Main orchestration - step-by-step execution |
| `references/data-inventory.md` | Scan local data sources for company |
| `references/agents.md` | Agent definitions and output schemas |
| `references/valuation.md` | Valuation functions and sector multiples |
| `references/output.md` | Display formatting and storage |

---

## Implementation Steps

### Step 1: Parse Input

Parse `/alpha <company> [context]` into structured input.

```python
parsed = parse_alpha_input(user_input)
# Returns: {'company': 'BETS-B', 'context': 'överväger att öka', 'is_ticker': True}
```

See: `references/workflow.md` - parse_alpha_input()

### Step 2: Data Inventory

Scan all local data sources for the company.

```python
inventory = inventory_company_data(company_query)
mode = inventory['summary']['mode']  # full | partial | discovery
```

See: `references/data-inventory.md`

### Step 3: Handle Missing Data

Display what's available, warn about gaps, confirm to proceed.

- **full mode**: Rich data - proceed with comprehensive analysis
- **partial mode**: Some data - supplement with external research
- **discovery mode**: Limited data - ask user to confirm before proceeding

### Step 4: Spawn Parallel Agents

Launch agents 1-4 simultaneously using Task tool:

| Agent | Data Source | Focus |
|-------|-------------|-------|
| FUNDAMENTA | Filings | Revenue, margins, cash flow, CEO credibility |
| SENTIMENT | Podcasts, Twitter, YouTube | Market sentiment, notable speakers |
| INSIDER | FI data | Net direction, significant trades |
| EXTERN | Web search | News, Reddit, analyst views, short interest |

See: `references/agents.md`

### Step 5: Collect Results

Gather JSON outputs from all agents, validate structure, note failures.

### Step 6: Risk Agent

Run RISKER agent after agents 1-4 complete. It synthesizes all findings to:

- Aggregate and rank all risks
- Identify blind spots
- Construct bear case
- Calculate worst-case valuation

See: `references/agents.md` - Agent 5

### Step 7: Peer Comparison

Suggest peers based on sector, allow user to confirm or modify.

### Step 8: Build Scenarios

Create Bull/Base/Bear scenarios with sector-appropriate multiples:

| Sector | Primary Multiple | Range |
|--------|-----------------|-------|
| Gaming/Betting | EV/EBITDA | 8-12x |
| SaaS/Tech | EV/Sales | 5-15x |
| Bank/Finans | P/B | 0.8-1.2x |
| Fastighet | P/NAV | 0.8-1.1x |
| Industri | EV/EBITDA | 7-10x |

See: `references/valuation.md`

### Step 9: Calculate Fair Value

Compute probability-weighted fair value from scenarios.

Default weights: Bull 25%, Base 50%, Bear 25%

### Step 10: Generate Verdict

Determine recommendation based on upside/downside:

| Verdict | Threshold |
|---------|-----------|
| KÖPVÄRD | >20% upside |
| ATTRAKTIV | 5-20% upside |
| FAIR | -10% to +5% |
| FULLVÄRDERAD | -20% to -10% |
| ÖVERVÄRDERAD | <-20% |

See: `references/valuation.md` - generate_verdict()

### Step 11: Save Analysis

Save complete analysis to `data/bolagsanalys/{ticker}/{date}-analysis.json`

See: `references/output.md`

---

## Agent Execution Matrix

| Agent | Runs In Parallel | Waits For | Spawned When |
|-------|-----------------|-----------|--------------|
| FUNDAMENTA | Yes | - | Filings exist |
| SENTIMENT | Yes | - | Podcasts/Twitter/YouTube exist |
| INSIDER | Yes | - | Insider data exists |
| EXTERN | Yes | - | Always |
| RISKER | No | Agents 1-4 | After parallel agents complete |
| SYNTHESIS | No | All | Final step |

---

## Output Format

```
============================================================
BOLAGSANALYS: Betsson (BETS-B)
============================================================
Mode: FULL - Rich local data available
------------------------------------------------------------
Data Sources:
    Filings:   8 reports
   Podcasts:  12 episodes
    Twitter:   2 accounts
    Insider:   3 files
------------------------------------------------------------
Total: 25 items across 5 sources
============================================================

[Agent findings displayed here...]

============================================================
                   VERDICT: ATTRAKTIV [**]
============================================================

Fair Value vs Price:
------------------------------------------------------------
  Viktat Fair Value:      112.50 SEK
  Nuvarande Pris:          95.00 SEK
  Uppsida:                +18.4%
  Margin of Safety:        15.6%
------------------------------------------------------------

Scenarios:
  Bull (25%):    140.00 SEK  (+47.4%)
  Base (50%):    115.00 SEK  (+21.1%)
  Bear (25%):     85.00 SEK  (-10.5%)

------------------------------------------------------------
Key Risks:
  - Regulatory tightening in key markets
  - Competition from new entrants
------------------------------------------------------------

Recommendation: ATTRAKTIV
Confidence: MEDIUM

Aktien handlas 18% under viktat fair value med medel konfidens.
Attraktiv nivåer. Notera 2 identifierade risker.
============================================================
```

---

## Interactive Follow-ups

After analysis, ask follow-up questions:

- "Berätta mer om bear case"
- "Vilka är de största riskerna?"
- "Jämför med peers"
- "Visa insideraktivitet"
- "Fördjupa i fundamenta"

---

## Example Session

```
User: /alpha BETS-B "funderar på att öka position"

Claude: [Runs data inventory]
        Found: 8 filings, 12 podcasts, 3 insider files
        Mode: FULL

        [Spawns 4 agents in parallel]
        [Collects results]
        [Runs risk synthesis]

        [Displays verdict: ATTRAKTIV, 18% upside]

        Analysis saved to: data/bolagsanalys/BETS-B/2025-01-15-analysis.json

User: Berätta mer om insiderhandeln

Claude: [Shows detailed insider analysis]
        Net direction: NET_BUYER
        CEO bought 50,000 shares at 92 SEK in December
        Cluster activity detected: 3 insiders buying in Q4

User: Exit

Claude: Session ended. Analysis available at saved path.
```

---

## Data Limitations Handling

When data is incomplete:

1. Flag missing sources clearly
2. Reduce confidence level
3. Note limitations in saved analysis
4. Suggest how to improve coverage:
   - `/download-reports` for filings
   - `/analyze` for podcast transcripts
   - `/insider` for transaction data

---

## Tips for Best Results

1. **Rich data = better analysis** - run skill on companies with existing local data
2. **Provide context** - helps tailor the analysis focus
3. **Review bear case** - most valuable part is what could go wrong
4. **Check peers** - relative valuation provides sanity check
5. **Save analyses** - track fair value vs price over time
