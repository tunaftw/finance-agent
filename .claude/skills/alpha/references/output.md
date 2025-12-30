# Output & Storage Module

Module for saving analyses and displaying results. Used after valuation to persist analyses and present final verdicts.

---

## Analysis JSON Schema

Full schema for saved analysis files.

**Path**: `data/bolagsanalys/{ticker}/{YYYY-MM-DD}-analysis.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": [
    "ticker",
    "company",
    "date",
    "weighted_fair_value",
    "current_price",
    "verdict"
  ],
  "properties": {
    "ticker": {
      "type": "string",
      "description": "Stock ticker symbol (e.g., 'EVO', 'BETS-B')"
    },
    "company": {
      "type": "string",
      "description": "Full company name"
    },
    "date": {
      "type": "string",
      "format": "date",
      "description": "Analysis date in YYYY-MM-DD format"
    },
    "weighted_fair_value": {
      "type": "number",
      "description": "Probability-weighted fair value per share"
    },
    "current_price": {
      "type": "number",
      "description": "Stock price at time of analysis"
    },
    "verdict": {
      "type": "object",
      "required": ["recommendation", "upside_pct", "confidence"],
      "properties": {
        "recommendation": {
          "type": "string",
          "enum": ["KOPVARD", "ATTRAKTIV", "FAIR", "FULLVARDERAD", "OVERVARDERAD"]
        },
        "upside_pct": {
          "type": "number",
          "description": "Percentage upside/downside to fair value"
        },
        "confidence": {
          "type": "string",
          "enum": ["high", "medium", "low"]
        },
        "risk_adjusted_verdict": {
          "type": "string",
          "description": "Verdict adjusted for risk count and confidence"
        },
        "summary": {
          "type": "string",
          "description": "Human-readable verdict summary"
        }
      }
    },
    "data_sources": {
      "type": "object",
      "description": "Summary of data sources used",
      "properties": {
        "mode": {
          "type": "string",
          "enum": ["full", "partial", "discovery"]
        },
        "filings_count": { "type": "integer" },
        "podcasts_count": { "type": "integer" },
        "twitter_count": { "type": "integer" },
        "youtube_count": { "type": "integer" },
        "insider_count": { "type": "integer" },
        "news_count": { "type": "integer" },
        "external_searches": { "type": "integer" }
      }
    },
    "fundamenta": {
      "type": "object",
      "description": "Output from FUNDAMENTA agent",
      "properties": {
        "revenue": {
          "type": "object",
          "properties": {
            "latest_annual": { "type": "number" },
            "cagr_3y": { "type": "number" },
            "trend": { "type": "string" }
          }
        },
        "margins": {
          "type": "object",
          "properties": {
            "ebit_margin": { "type": "number" },
            "ebit_margin_trend": { "type": "string" }
          }
        },
        "balance_sheet": {
          "type": "object",
          "properties": {
            "net_debt": { "type": "number" },
            "net_debt_ebitda": { "type": "number" },
            "health": { "type": "string" }
          }
        },
        "quality_score": { "type": "integer" },
        "ceo_credibility": { "type": "string" },
        "red_flags": {
          "type": "array",
          "items": { "type": "string" }
        },
        "summary": { "type": "string" }
      }
    },
    "sentiment": {
      "type": "object",
      "description": "Output from SENTIMENT agent",
      "properties": {
        "overall_score": { "type": "number" },
        "label": {
          "type": "string",
          "enum": ["very_bullish", "bullish", "neutral", "bearish", "very_bearish"]
        },
        "trend": { "type": "string" },
        "notable_speakers": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name": { "type": "string" },
              "stance": { "type": "string" },
              "argument": { "type": "string" }
            }
          }
        },
        "bull_arguments": {
          "type": "array",
          "items": { "type": "string" }
        },
        "bear_arguments": {
          "type": "array",
          "items": { "type": "string" }
        },
        "summary": { "type": "string" }
      }
    },
    "insider": {
      "type": "object",
      "description": "Output from INSIDER agent",
      "properties": {
        "net_direction": {
          "type": "string",
          "enum": ["net_buyer", "net_seller", "neutral"]
        },
        "net_value_sek": { "type": "number" },
        "significant_transactions": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "date": { "type": "string" },
              "insider": { "type": "string" },
              "type": { "type": "string" },
              "value": { "type": "number" }
            }
          }
        },
        "cluster_activity": { "type": "boolean" },
        "signal_strength": { "type": "integer" },
        "summary": { "type": "string" }
      }
    },
    "risks": {
      "type": "object",
      "description": "Output from RISKER agent",
      "properties": {
        "overall_score": { "type": "integer" },
        "top_risks": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "risk": { "type": "string" },
              "category": { "type": "string" },
              "probability": { "type": "string" },
              "impact": { "type": "string" }
            }
          }
        },
        "red_flags": {
          "type": "array",
          "items": { "type": "string" }
        },
        "bear_thesis": { "type": "string" },
        "kill_the_thesis": { "type": "string" },
        "summary": { "type": "string" }
      }
    },
    "peers": {
      "type": "object",
      "description": "Peer comparison data",
      "properties": {
        "peer_group": {
          "type": "array",
          "items": { "type": "string" }
        },
        "relative_valuation": {
          "type": "object",
          "properties": {
            "vs_peers_pe": { "type": "string" },
            "vs_peers_ev_ebitda": { "type": "string" }
          }
        },
        "notes": { "type": "string" }
      }
    },
    "scenarios": {
      "type": "array",
      "description": "Bull/Base/Bear valuation scenarios",
      "items": {
        "type": "object",
        "required": ["name", "probability", "fair_value"],
        "properties": {
          "name": {
            "type": "string",
            "enum": ["Bull", "Base", "Bear"]
          },
          "probability": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
          },
          "ebitda": { "type": "number" },
          "multiple": { "type": "number" },
          "ev": { "type": "number" },
          "equity_value": { "type": "number" },
          "fair_value": { "type": "number" },
          "key_assumptions": {
            "type": "array",
            "items": { "type": "string" }
          }
        }
      }
    },
    "position_guidance": {
      "type": "object",
      "properties": {
        "sizing": {
          "type": "string",
          "enum": ["full", "half", "starter", "avoid"]
        },
        "entry_zone": {
          "type": "object",
          "properties": {
            "lower": { "type": "number" },
            "upper": { "type": "number" }
          }
        },
        "stop_loss": { "type": "number" },
        "take_profit": {
          "type": "array",
          "items": { "type": "number" }
        }
      }
    },
    "next_catalyst": {
      "type": "object",
      "properties": {
        "event": { "type": "string" },
        "date": { "type": "string" },
        "impact": { "type": "string" }
      }
    },
    "metadata": {
      "type": "object",
      "properties": {
        "analysis_version": { "type": "string" },
        "created_at": { "type": "string", "format": "date-time" },
        "data_limitations": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    }
  }
}
```

---

## Python Functions

### save_analysis()

Save analysis to disk with proper directory structure.

```python
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Union


def save_analysis(analysis: dict) -> str:
    """
    Save analysis dict to disk in standardized location.

    Args:
        analysis: Complete analysis dict with required fields:
            - ticker: Stock ticker (e.g., 'EVO', 'BETS-B')
            - company: Company name
            - date: Analysis date (YYYY-MM-DD string or will use today)
            - weighted_fair_value: Calculated fair value
            - current_price: Price at analysis time
            - verdict: Verdict dict with recommendation

    Returns:
        Absolute path to saved file

    Raises:
        ValueError: If required fields are missing

    Example:
        >>> analysis = {
        ...     'ticker': 'EVO',
        ...     'company': 'Evolution Gaming',
        ...     'date': '2025-01-15',
        ...     'weighted_fair_value': 1250.0,
        ...     'current_price': 1100.0,
        ...     'verdict': {
        ...         'recommendation': 'ATTRAKTIV',
        ...         'upside_pct': 13.6,
        ...         'confidence': 'medium'
        ...     },
        ...     'scenarios': [...],
        ...     'fundamenta': {...},
        ...     'sentiment': {...}
        ... }
        >>> path = save_analysis(analysis)
        >>> print(path)
        'data/bolagsanalys/EVO/2025-01-15-analysis.json'
    """
    # Validate required fields
    required_fields = ['ticker', 'company', 'weighted_fair_value', 'current_price', 'verdict']
    missing = [f for f in required_fields if f not in analysis]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    # Validate verdict structure
    verdict = analysis.get('verdict', {})
    if 'recommendation' not in verdict:
        raise ValueError("verdict must contain 'recommendation' field")

    # Get or set date
    if 'date' not in analysis or not analysis['date']:
        analysis['date'] = datetime.now().strftime('%Y-%m-%d')

    # Normalize ticker (uppercase, handle suffixes)
    ticker = analysis['ticker'].upper().replace('.ST', '')

    # Build path
    base_path = Path("data/bolagsanalys")
    company_dir = base_path / ticker
    filename = f"{analysis['date']}-analysis.json"
    file_path = company_dir / filename

    # Create directory if needed
    try:
        company_dir.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        raise IOError(f"Cannot create directory {company_dir}: {e}") from e

    # Add metadata
    if 'metadata' not in analysis:
        analysis['metadata'] = {}
    analysis['metadata']['created_at'] = datetime.now().isoformat()
    analysis['metadata']['analysis_version'] = '1.0'

    # Save with pretty formatting
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
    except (PermissionError, OSError) as e:
        raise IOError(f"Cannot write to {file_path}: {e}") from e

    return str(file_path)
```

---

### display_header()

Display analysis header with company info and data sources.

```python
def display_header(
    company: str,
    ticker: str,
    inventory: dict,
    mode: str = None
) -> str:
    """
    Display analysis header with company info and data source summary.

    Args:
        company: Company name
        ticker: Stock ticker
        inventory: Data inventory dict from inventory_company_data()
        mode: Override mode ('full', 'partial', 'discovery') or use from inventory

    Returns:
        Formatted header string for display

    Example:
        >>> inventory = {
        ...     'summary': {'mode': 'full', 'total_sources': 5, 'total_items': 23},
        ...     'sources': {
        ...         'filings': {'count': 8},
        ...         'podcasts': {'count': 12},
        ...         'twitter': {'count': 2},
        ...         'insider': {'count': 1}
        ...     }
        ... }
        >>> print(display_header('Evolution Gaming', 'EVO', inventory))

        ============================================================
        BOLAGSANALYS: Evolution Gaming (EVO)
        ============================================================
        Mode: FULL - Rich local data available
        ------------------------------------------------------------
        Data Sources:
          Filings:   8 reports
          Podcasts: 12 episodes
          Twitter:   2 accounts
          Insider:   1 file
        ------------------------------------------------------------
        Total: 23 items across 5 sources
        ============================================================
    """
    lines = []
    separator = "=" * 60
    dash_line = "-" * 60

    # Header
    lines.append("")
    lines.append(separator)
    lines.append(f"BOLAGSANALYS: {company} ({ticker})")
    lines.append(separator)

    # Mode
    summary = inventory.get('summary', {})
    analysis_mode = mode or summary.get('mode', 'discovery')

    mode_descriptions = {
        'full': 'Rich local data available',
        'partial': 'Some local data - supplement with research',
        'discovery': 'Limited data - focus on thesis development'
    }

    lines.append(f"Mode: {analysis_mode.upper()} - {mode_descriptions.get(analysis_mode, '')}")
    lines.append(dash_line)

    # Data sources
    sources = inventory.get('sources', {})

    if sources:
        lines.append("Data Sources:")

        source_labels = {
            'filings': ('Filings', 'reports'),
            'podcasts': ('Podcasts', 'episodes'),
            'twitter': ('Twitter', 'accounts'),
            'youtube': ('YouTube', 'videos'),
            'insider': ('Insider', 'files'),
            'news': ('News', 'items'),
            'database': ('Database', 'records'),
            'prices': ('Prices', 'available')
        }

        for source_key, (label, unit) in source_labels.items():
            if source_key in sources:
                src = sources[source_key]
                count = src.get('count', 1 if src.get('available') else 0)
                if count > 0:
                    lines.append(f"  {label:>10}: {count:>3} {unit}")
    else:
        lines.append("Data Sources: None found")

    lines.append(dash_line)

    # Summary
    total_items = summary.get('total_items', 0)
    total_sources = summary.get('total_sources', 0)
    lines.append(f"Total: {total_items} items across {total_sources} sources")
    lines.append(separator)

    return "\n".join(lines)
```

---

### display_verdict()

Display the final verdict with valuation details.

```python
def display_verdict(
    company: str,
    ticker: str,
    weighted_fair_value: float,
    current_price: float,
    verdict: dict,
    scenarios: list[dict],
    key_risks: list[str] = None
) -> str:
    """
    Display the final analysis verdict with valuation details.

    Args:
        company: Company name
        ticker: Stock ticker
        weighted_fair_value: Probability-weighted fair value per share
        current_price: Current stock price
        verdict: Verdict dict from generate_verdict()
        scenarios: List of scenario dicts from build_scenarios()
        key_risks: Optional list of key risk strings

    Returns:
        Formatted verdict string for display

    Raises:
        ValueError: If current_price is not greater than 0

    Example:
        >>> verdict = {
        ...     'recommendation': 'ATTRAKTIV',
        ...     'upside_pct': 21.4,
        ...     'confidence': 'medium',
        ...     'risk_adjusted_verdict': 'ATTRAKTIV',
        ...     'margin_of_safety': 17.6,
        ...     'summary': 'Aktien handlas 21% under viktat fair value...'
        ... }
        >>> scenarios = [
        ...     {'name': 'Bull', 'fair_value': 1400, 'probability': 0.25},
        ...     {'name': 'Base', 'fair_value': 1150, 'probability': 0.50},
        ...     {'name': 'Bear', 'fair_value': 850, 'probability': 0.25}
        ... ]
        >>> print(display_verdict('Betsson', 'BETS-B', 1112.5, 950, verdict, scenarios))

        ============================================================
                           VERDICT: ATTRAKTIV
        ============================================================

        Fair Value vs Price:
        ------------------------------------------------------------
          Viktat Fair Value:    1,112.50 SEK
          Nuvarande Pris:         950.00 SEK
          Uppsida:                +17.1%
          Margin of Safety:       17.6%
        ------------------------------------------------------------

        Scenarios:
          Bull (25%):  1,400.00 SEK  (+47.4%)
          Base (50%):  1,150.00 SEK  (+21.1%)
          Bear (25%):    850.00 SEK  (-10.5%)

        ------------------------------------------------------------
        Key Risks:
          - Regulatory tightening in key markets
          - Competition from new entrants
        ------------------------------------------------------------

        Recommendation: ATTRAKTIV
        Confidence: MEDIUM

        Aktien handlas 21% under viktat fair value med medel konfidens.
        Attraktiv nivaer. Notera 2 identifierade risker.
        ============================================================
    """
    if current_price <= 0:
        raise ValueError("current_price must be greater than 0")

    lines = []
    separator = "=" * 60
    dash_line = "-" * 60

    # Verdict emojis
    verdict_emojis = {
        'KOPVARD': '[***]',      # Strong buy
        'ATTRAKTIV': '[**]',    # Buy
        'FAIR': '[=]',          # Hold
        'FULLVARDERAD': '[-]',  # Reduce
        'OVERVARDERAD': '[--]'  # Sell
    }

    recommendation = verdict.get('risk_adjusted_verdict', verdict.get('recommendation', 'FAIR'))
    emoji = verdict_emojis.get(recommendation, '')

    # Header
    lines.append("")
    lines.append(separator)
    lines.append(f"                   VERDICT: {recommendation} {emoji}".center(60))
    lines.append(separator)
    lines.append("")

    # Fair value vs price
    lines.append("Fair Value vs Price:")
    lines.append(dash_line)

    upside_pct = verdict.get('upside_pct', ((weighted_fair_value - current_price) / current_price) * 100)
    margin_of_safety = verdict.get('margin_of_safety', 0)

    upside_sign = '+' if upside_pct >= 0 else ''

    lines.append(f"  Viktat Fair Value: {weighted_fair_value:>12,.2f} SEK")
    lines.append(f"  Nuvarande Pris:    {current_price:>12,.2f} SEK")
    lines.append(f"  Uppsida:           {upside_sign}{upside_pct:>11.1f}%")
    lines.append(f"  Margin of Safety:  {margin_of_safety:>11.1f}%")
    lines.append(dash_line)
    lines.append("")

    # Scenarios
    lines.append("Scenarios:")
    for scenario in scenarios:
        name = scenario['name']
        prob = scenario.get('probability', 0) * 100
        fv = scenario['fair_value']
        pct = ((fv - current_price) / current_price) * 100
        pct_sign = '+' if pct >= 0 else ''
        lines.append(f"  {name} ({prob:.0f}%): {fv:>10,.2f} SEK  ({pct_sign}{pct:.1f}%)")
    lines.append("")

    # Key risks
    if key_risks:
        lines.append(dash_line)
        lines.append("Key Risks:")
        for risk in key_risks[:5]:  # Limit to top 5
            # Truncate long risks
            risk_text = risk[:55] + "..." if len(risk) > 55 else risk
            lines.append(f"  - {risk_text}")
        lines.append(dash_line)
        lines.append("")

    # Recommendation
    confidence = verdict.get('confidence', 'medium').upper()
    lines.append(f"Recommendation: {recommendation}")
    lines.append(f"Confidence: {confidence}")
    lines.append("")

    # Summary
    summary = verdict.get('summary', '')
    if summary:
        # Word wrap summary
        words = summary.split()
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= 58:
                current_line += (" " if current_line else "") + word
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

    lines.append(separator)

    return "\n".join(lines)
```

---

## Usage Example

Complete output workflow:

```python
from datetime import datetime

# After analysis is complete with all components...

# 1. Display header
inventory = inventory_company_data("Betsson")
header = display_header(
    company="Betsson",
    ticker="BETS-B",
    inventory=inventory
)
print(header)

# 2. Run valuation
scenarios = build_scenarios(
    base_ebitda=3500,
    base_multiple=9.0,
    net_debt=-2000,  # Net cash
    shares=150
)

fv_result = calculate_fair_value(scenarios)
weighted_fv = fv_result['weighted_fair_value']

verdict = generate_verdict(
    weighted_fv=weighted_fv,
    current_price=95.0,
    confidence='medium',
    scenarios=scenarios,
    key_risks=['Regulatory risk', 'Market share decline']
)

# 3. Display verdict
verdict_output = display_verdict(
    company="Betsson",
    ticker="BETS-B",
    weighted_fair_value=weighted_fv,
    current_price=95.0,
    verdict=verdict,
    scenarios=scenarios,
    key_risks=['Regulatory risk', 'Market share decline']
)
print(verdict_output)

# 4. Compile and save analysis
analysis = {
    'ticker': 'BETS-B',
    'company': 'Betsson',
    'date': datetime.now().strftime('%Y-%m-%d'),
    'weighted_fair_value': weighted_fv,
    'current_price': 95.0,
    'verdict': verdict,
    'scenarios': scenarios,
    'data_sources': {
        'mode': inventory['summary']['mode'],
        'filings_count': inventory['sources'].get('filings', {}).get('count', 0),
        'podcasts_count': inventory['sources'].get('podcasts', {}).get('count', 0)
    },
    'fundamenta': {...},  # From Agent 1
    'sentiment': {...},   # From Agent 2
    'insider': {...},     # From Agent 3
    'risks': {...}        # From Agent 5
}

saved_path = save_analysis(analysis)
print(f"\nAnalysis saved to: {saved_path}")
```

---

## File Organization

```
data/bolagsanalys/
  EVO/
    2025-01-15-analysis.json
    2025-02-20-analysis.json
  BETS-B/
    2025-01-10-analysis.json
  INVE-B/
    2025-01-22-analysis.json
```

Each company gets its own subdirectory. Multiple analyses over time are preserved, enabling historical tracking of fair value estimates vs actual price movements.

---

## Loading Previous Analyses

```python
def load_latest_analysis(ticker: str) -> dict | None:
    """
    Load the most recent analysis for a ticker.

    Args:
        ticker: Stock ticker

    Returns:
        Analysis dict or None if not found
    """
    from pathlib import Path
    import json

    ticker = ticker.upper().replace('.ST', '')
    base_path = Path("data/bolagsanalys")
    company_dir = base_path / ticker

    if not company_dir.exists():
        return None

    # Find most recent analysis file
    analysis_files = sorted(company_dir.glob("*-analysis.json"), reverse=True)

    if not analysis_files:
        return None

    try:
        with open(analysis_files[0], 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, PermissionError, IOError) as e:
        return None  # Or raise with context


def list_analyses(ticker: str = None) -> list[dict]:
    """
    List all saved analyses, optionally filtered by ticker.

    Args:
        ticker: Optional ticker to filter by

    Returns:
        List of dicts with ticker, date, recommendation, upside_pct
    """
    from pathlib import Path
    import json

    base_path = Path("data/bolagsanalys")
    results = []

    if ticker:
        ticker = ticker.upper().replace('.ST', '')
        search_dirs = [base_path / ticker] if (base_path / ticker).exists() else []
    else:
        search_dirs = [d for d in base_path.iterdir() if d.is_dir()]

    for company_dir in search_dirs:
        for analysis_file in company_dir.glob("*-analysis.json"):
            try:
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results.append({
                        'ticker': data.get('ticker'),
                        'company': data.get('company'),
                        'date': data.get('date'),
                        'recommendation': data.get('verdict', {}).get('recommendation'),
                        'upside_pct': data.get('verdict', {}).get('upside_pct'),
                        'file': str(analysis_file)
                    })
            except (json.JSONDecodeError, KeyError):
                continue

    return sorted(results, key=lambda x: x['date'], reverse=True)
```
