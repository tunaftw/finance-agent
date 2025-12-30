# Filing Analysis Output Schema

JSON-schema for filing-analyser.

## Per-Filing Analysis

```json
{
  "filing_id": "getinge-annual-2024",
  "company_id": "getinge",
  "filing_type": "annual",
  "fiscal_year": 2024,
  "fiscal_quarter": null,
  "analyzed_at": "2024-12-29T10:00:00Z",
  "model_used": "claude-sonnet-4-20250514",

  "executive_summary": "2-3 meningar som sammanfattar filingen...",
  "key_highlights": [
    "Organisk tillvaxt 5.2% overtraffade mal",
    "Marginalexpansion +120bp YoY",
    "Ny produktplattform forsenad till Q4"
  ],

  "ceo_letter": {
    "author": "Mattias Perjos",
    "title": "CEO",
    "word_count": 1850,
    "tone": "cautiously_optimistic",
    "confidence_level": "medium",

    "promises": [
      {
        "statement": "We expect organic growth of 4-6% for full year 2024",
        "metric": "organic_growth",
        "target": "4-6%",
        "timeframe": "FY 2024",
        "confidence_language": "expect"
      },
      {
        "statement": "Operating margin target of 15-16% remains",
        "metric": "operating_margin",
        "target": "15-16%",
        "timeframe": "medium_term",
        "confidence_language": "target"
      }
    ],

    "themes": [
      {
        "topic": "operational_efficiency",
        "emphasis": "high",
        "sentiment": "positive"
      },
      {
        "topic": "supply_chain",
        "emphasis": "medium",
        "sentiment": "improving"
      },
      {
        "topic": "china_recovery",
        "emphasis": "medium",
        "sentiment": "cautious"
      }
    ],

    "challenges": [
      {
        "challenge": "Hospital capex delays in Europe",
        "attribution": "external",
        "tone": "explanatory"
      },
      {
        "challenge": "Product launch delay",
        "attribution": "internal",
        "tone": "accountable"
      }
    ],

    "honesty_signals": [
      "Acknowledges margin pressure from inflation",
      "Admits slower-than-expected recovery in China",
      "Discusses specific product launch delay openly"
    ],

    "key_quotes": [
      {
        "quote": "We remain committed to our long-term margin targets despite near-term headwinds",
        "category": "commitment"
      },
      {
        "quote": "The delay in our ventilator platform launch was disappointing but necessary for quality",
        "category": "accountability"
      }
    ],

    "is_qa_format": false,
    "questions_addressed": []
  },

  "mda_analysis": {
    "key_narratives": [
      "Strong order intake in Acute Care Therapies",
      "Life Science segment recovering after destocking",
      "Surgical Workflows stable despite market challenges"
    ],
    "management_interpretation": "Management views Q3 as confirmation of turnaround trajectory, emphasizing operational improvements rather than market recovery.",

    "segment_commentary": {
      "Acute Care Therapies": {
        "name": "Acute Care Therapies",
        "performance": "strong",
        "revenue_growth_yoy": 0.08,
        "operating_margin": 0.18,
        "outlook": "positive",
        "management_commentary": "Strong performance driven by ventilator demand"
      },
      "Life Science": {
        "name": "Life Science",
        "performance": "recovering",
        "revenue_growth_yoy": 0.02,
        "operating_margin": 0.12,
        "outlook": "cautious",
        "management_commentary": "Recovery slower than expected"
      },
      "Surgical Workflows": {
        "name": "Surgical Workflows",
        "performance": "stable",
        "revenue_growth_yoy": 0.04,
        "operating_margin": 0.15,
        "outlook": "neutral",
        "management_commentary": "Stable despite capex headwinds"
      }
    },

    "operational_highlights": [
      "New manufacturing facility in Poland ramping up",
      "20% reduction in lead times achieved"
    ],

    "concerns_mentioned": [
      "European hospital capex remains weak",
      "China recovery slower than anticipated"
    ]
  },

  "risk_factors": {
    "risks": [
      {
        "risk": "Regulatory changes in medical device approval",
        "severity": "high",
        "category": "regulatory",
        "change": "unchanged",
        "is_boilerplate": false
      },
      {
        "risk": "AI regulatory uncertainty in medical devices",
        "severity": "medium",
        "category": "regulatory",
        "change": "new",
        "is_boilerplate": false
      },
      {
        "risk": "Supply chain disruptions",
        "severity": "medium",
        "category": "operational",
        "change": "de-escalated",
        "is_boilerplate": false
      },
      {
        "risk": "Currency fluctuations",
        "severity": "low",
        "category": "financial",
        "change": "unchanged",
        "is_boilerplate": true
      }
    ],

    "new_risks_count": 1,
    "removed_risks_count": 0,
    "escalated_risks_count": 0,
    "de_escalated_risks_count": 1,
    "boilerplate_ratio": 0.25,
    "top_risk_categories": ["regulatory", "operational"]
  },

  "guidance": {
    "targets": [
      {
        "metric": "organic_growth",
        "value": "4-6%",
        "period": "FY 2024",
        "vs_previous": "maintained",
        "notes": null
      },
      {
        "metric": "operating_margin",
        "value": "15-16%",
        "period": "medium_term",
        "vs_previous": "maintained",
        "notes": "Medium-term = 3-5 years"
      },
      {
        "metric": "eps_growth",
        "value": ">12%",
        "period": "2024-2028",
        "vs_previous": "new",
        "notes": "Average annual growth"
      }
    ],
    "overall_direction": "maintained",
    "commentary": "Full year guidance maintained despite Q3 headwinds in Europe",
    "management_confidence": "medium"
  },

  "segments": [
    {
      "name": "Acute Care Therapies",
      "revenue": 3500000000,
      "revenue_growth_yoy": 0.08,
      "operating_margin": 0.18,
      "order_intake": 3800000000,
      "order_intake_growth_yoy": 0.05,
      "management_commentary": "Strong performance driven by ventilator demand",
      "outlook": "positive",
      "management_focus": "high"
    },
    {
      "name": "Life Science",
      "revenue": 2100000000,
      "revenue_growth_yoy": 0.02,
      "operating_margin": 0.12,
      "order_intake": 2200000000,
      "order_intake_growth_yoy": 0.03,
      "management_commentary": "Recovery slower than expected",
      "outlook": "cautious",
      "management_focus": "medium"
    },
    {
      "name": "Surgical Workflows",
      "revenue": 2600000000,
      "revenue_growth_yoy": 0.04,
      "operating_margin": 0.15,
      "order_intake": 2700000000,
      "order_intake_growth_yoy": 0.04,
      "management_commentary": "Stable despite capex headwinds",
      "outlook": "neutral",
      "management_focus": "low"
    }
  ],

  "financial_metrics": {
    "revenue": 8200000000,
    "operating_income": 1100000000,
    "net_income": 850000000,
    "operating_margin": 0.134,
    "net_margin": 0.104,
    "eps": 2.45,
    "free_cash_flow": 920000000,
    "net_debt": 12000000000,
    "roe": 0.18,
    "roic": 0.12
  }
}
```

## Field Definitions

### Top Level

| Falt | Typ | Beskrivning |
|------|-----|-------------|
| `filing_id` | string | Unik ID: `{company}-{type}-{year}[-q{quarter}]` |
| `company_id` | string | Bolags-ID (lowercase) |
| `filing_type` | enum | `annual` \| `quarterly` |
| `fiscal_year` | int | Rakneskapsaret |
| `fiscal_quarter` | int? | 1-4 for kvartalsrapporter, null for arsrapporter |
| `analyzed_at` | ISO8601 | Tidsstampel for analysen |
| `model_used` | string | Modell som anvandes |

### CEO Letter

| Falt | Typ | Beskrivning |
|------|-----|-------------|
| `tone` | enum | `optimistic` \| `cautiously_optimistic` \| `neutral` \| `cautious` \| `defensive` |
| `confidence_level` | enum | `high` \| `medium` \| `low` |
| `promises[].metric` | string | `organic_growth` \| `operating_margin` \| `revenue` \| `eps` \| `ebitda_margin` \| annan |
| `promises[].confidence_language` | string | `expect` \| `target` \| `aim` \| `committed` \| `hope` \| `will` |
| `themes[].emphasis` | enum | `high` \| `medium` \| `low` |
| `themes[].sentiment` | enum | `positive` \| `neutral` \| `negative` \| `improving` \| `declining` |
| `challenges[].attribution` | enum | `external` \| `internal` \| `mixed` |
| `challenges[].tone` | enum | `explanatory` \| `defensive` \| `dismissive` \| `accountable` |
| `key_quotes[].category` | enum | `commitment` \| `vision` \| `warning` \| `achievement` \| `excuse` \| `accountability` |

### Risk Factors

| Falt | Typ | Beskrivning |
|------|-----|-------------|
| `risks[].severity` | enum | `high` \| `medium` \| `low` |
| `risks[].category` | enum | `regulatory` \| `operational` \| `market` \| `financial` \| `legal` \| `technology` \| `other` |
| `risks[].change` | enum | `unchanged` \| `new` \| `escalated` \| `de-escalated` \| `removed` |
| `boilerplate_ratio` | float | 0.0-1.0, andel generiska risker |

### Guidance

| Falt | Typ | Beskrivning |
|------|-----|-------------|
| `targets[].metric` | string | Nyckeltal som mal galler |
| `targets[].vs_previous` | enum | `raised` \| `maintained` \| `lowered` \| `withdrawn` \| `new` |
| `overall_direction` | enum | `raised` \| `maintained` \| `lowered` |
| `management_confidence` | enum | `high` \| `medium` \| `low` |

### Segments

| Falt | Typ | Beskrivning |
|------|-----|-------------|
| `revenue` | int | Revenue i lokal valuta |
| `revenue_growth_yoy` | float | Tillvaxt som decimal (0.08 = 8%) |
| `operating_margin` | float | Marginal som decimal (0.18 = 18%) |
| `outlook` | enum | `positive` \| `neutral` \| `cautious` \| `negative` |
| `management_focus` | enum | `high` \| `medium` \| `low` |

## Evolution Schema (Cross-Filing)

For att spara utveckling over tid:

```json
{
  "company_id": "getinge",
  "last_updated": "2024-12-29T10:00:00Z",
  "filings_analyzed": ["annual-2023", "q1-2024", "q2-2024", "q3-2024"],

  "promise_tracker": [
    {
      "promise": "Organic growth 4-6% in 2024",
      "made_in": "annual-2023",
      "current_status": "on_track",
      "evidence": "YTD organic growth at 5.2%",
      "mentions": ["q1-2024", "q2-2024", "q3-2024"]
    }
  ],

  "tone_trajectory": [
    {"period": "annual-2023", "tone": "optimistic", "confidence": "high"},
    {"period": "q1-2024", "tone": "optimistic", "confidence": "high"},
    {"period": "q2-2024", "tone": "cautious", "confidence": "medium"},
    {"period": "q3-2024", "tone": "cautiously_optimistic", "confidence": "medium"}
  ],

  "guidance_accuracy": {
    "historical": [
      {"year": 2023, "metric": "organic_growth", "guided": "3-5%", "actual": "4.2%", "status": "met"}
    ],
    "accuracy_rate": 0.75
  },

  "signals": {
    "green_flags": ["Consistent promise delivery", "Improving margins"],
    "red_flags": ["Product launch delayed twice"],
    "watch_items": ["China recovery pace"]
  }
}
```
