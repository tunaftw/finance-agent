# Main Workflow

Complete orchestration for Alpha Extractor skill execution.

---

## Input Parsing

### parse_alpha_input()

Parse the `/alpha` command into company and context.

```python
import re
from typing import Optional

def parse_alpha_input(input_string: str) -> dict:
    """
    Parse /alpha command input into company and context.

    Handles formats:
        /alpha BETS-B
        /alpha Betsson
        /alpha EVO "considering adding to position"
        /alpha "Evolution Gaming" overväger att öka
        /alpha INVE-B nytt case, känner inte bolaget

    Args:
        input_string: Raw input after /alpha command

    Returns:
        Dict with:
            - company: Company name or ticker (normalized)
            - context: Optional user context string
            - is_ticker: True if input looks like a ticker

    Example:
        >>> parse_alpha_input('BETS-B "överväger att öka"')
        {'company': 'BETS-B', 'context': 'överväger att öka', 'is_ticker': True}

        >>> parse_alpha_input('Evolution Gaming funderar på position')
        {'company': 'Evolution Gaming', 'context': 'funderar på position', 'is_ticker': False}
    """
    input_string = input_string.strip()

    if not input_string:
        return {'company': None, 'context': None, 'is_ticker': False}

    # Pattern 1: Quoted company name followed by context
    # Example: "Evolution Gaming" some context here
    quoted_match = re.match(r'^"([^"]+)"\s*(.*)$', input_string)
    if quoted_match:
        company = quoted_match.group(1).strip()
        context = quoted_match.group(2).strip() or None
        is_ticker = _is_ticker(company)
        return {'company': company, 'context': context, 'is_ticker': is_ticker}

    # Pattern 2: Ticker/word followed by quoted context
    # Example: BETS-B "some context"
    ticker_quoted_match = re.match(r'^(\S+)\s+"([^"]+)"(.*)$', input_string)
    if ticker_quoted_match:
        company = ticker_quoted_match.group(1).strip()
        context = ticker_quoted_match.group(2).strip()
        extra = ticker_quoted_match.group(3).strip()
        if extra:
            context = f"{context} {extra}"
        is_ticker = _is_ticker(company)
        return {'company': company, 'context': context, 'is_ticker': is_ticker}

    # Pattern 3: Single word (ticker or short name) with optional unquoted context
    # Example: EVO considering position
    parts = input_string.split(maxsplit=1)
    if len(parts) == 1:
        company = parts[0]
        context = None
    else:
        first_word = parts[0]
        rest = parts[1]

        # Heuristic: If first word looks like a ticker, rest is context
        if _is_ticker(first_word):
            company = first_word
            context = rest
        else:
            # Check if we have a multi-word company name
            # Look for common context keywords to split on
            context_keywords = ['överväger', 'funderar', 'har i', 'nytt case',
                               'vill', 'considering', 'want to', 'looking at']

            split_point = None
            for keyword in context_keywords:
                if keyword in rest.lower():
                    idx = rest.lower().find(keyword)
                    # Include any preceding words in company name
                    if idx > 0:
                        company = f"{first_word} {rest[:idx].strip()}"
                        context = rest[idx:].strip()
                        split_point = idx
                        break

            if split_point is None:
                # No context keyword found - treat first word as company
                company = first_word
                context = rest

    is_ticker = _is_ticker(company)
    return {'company': company, 'context': context, 'is_ticker': is_ticker}


def _is_ticker(s: str) -> bool:
    """
    Heuristic to determine if string looks like a stock ticker.

    Tickers are typically:
        - 1-5 uppercase letters
        - May have suffix like -A, -B, .ST
        - All caps or mostly caps

    Examples:
        EVO -> True
        BETS-B -> True
        Evolution -> False
        INVE-B.ST -> True
    """
    if not s:
        return False

    # Remove common suffixes for check
    clean = s.upper().replace('.ST', '').replace('-A', '').replace('-B', '')

    # Ticker pattern: 1-5 uppercase letters/numbers
    if re.match(r'^[A-Z0-9]{1,5}$', clean):
        # Check if original was mostly uppercase
        alpha_chars = [c for c in s if c.isalpha()]
        if alpha_chars:
            upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
            return upper_ratio > 0.5

    return False
```

---

## Workflow Steps

### Step 1: Parse Input

```python
# Parse the /alpha command
parsed = parse_alpha_input(user_input)

if not parsed['company']:
    print("Usage: /alpha <company/ticker> [context]")
    print("Example: /alpha BETS-B 'överväger att öka position'")
    return

company_query = parsed['company']
user_context = parsed['context']
```

### Step 2: Run Data Inventory

Reference: `data-inventory.md`

```python
# Scan all local data sources
from references.data_inventory import inventory_company_data, display_inventory

inventory = inventory_company_data(company_query)
print(display_inventory(inventory))

# Store mode for later use
analysis_mode = inventory['summary']['mode']
```

### Step 3: Handle Missing Data

```python
# Check what data is available and warn about gaps
sources = inventory['sources']
mode = inventory['summary']['mode']

if mode == 'discovery':
    print("\n⚠️  LIMITED DATA AVAILABLE")
    print("This analysis will rely heavily on external research.")
    print("\nTo improve data coverage, consider running:")

    if 'filings' not in sources:
        print(f"  /download-reports {company_query}")

    if 'podcasts' not in sources:
        print(f"  Check if {company_query} is mentioned in unanalyzed podcasts")

    # Ask user to confirm proceeding
    response = input("\nContinue with limited data? (y/n): ")
    if response.lower() != 'y':
        print("Analysis cancelled. Gather more data first.")
        return

elif mode == 'partial':
    print("\n📊 PARTIAL DATA - will supplement with external research")
    missing = []
    if 'filings' not in sources:
        missing.append("financial reports")
    if 'insider' not in sources:
        missing.append("insider transactions")
    if missing:
        print(f"Missing: {', '.join(missing)}")
```

### Step 4: Spawn Parallel Agents

Reference: `agents.md`

```python
# Spawn agents 1-4 in parallel using Task tool
# These agents have no dependencies on each other

from concurrent.futures import ThreadPoolExecutor, as_completed

agent_tasks = []

# Only spawn agents for available data
if 'filings' in sources:
    agent_tasks.append({
        'agent': 'fundamenta',
        'prompt': build_fundamenta_prompt(company_query, sources['filings'])
    })

if any(k in sources for k in ['podcasts', 'twitter', 'youtube']):
    agent_tasks.append({
        'agent': 'sentiment',
        'prompt': build_sentiment_prompt(company_query, sources)
    })

if 'insider' in sources:
    agent_tasks.append({
        'agent': 'insider_agare',
        'prompt': build_insider_prompt(company_query, sources['insider'])
    })

# External research always runs (uses web search)
agent_tasks.append({
    'agent': 'extern_research',
    'prompt': build_extern_prompt(company_query, user_context)
})

# Execute in parallel via Task tool
# In Claude Code, use Task tool for each agent
results = {}
for task in agent_tasks:
    # Task tool invocation happens here
    # result = Task(task['prompt'])
    # results[task['agent']] = result
    pass
```

**Note on Prompt Builders:**

The functions `build_fundamenta_prompt()`, `build_sentiment_prompt()`, `build_insider_prompt()`, and `build_extern_prompt()` are pseudo-code patterns. When executing, Claude should construct prompts directly using the templates defined in `agents.md`.

**Task Tool Invocation Pattern:**

```
Use the Task tool to spawn each agent. Example:

Task: "Run FUNDAMENTA agent for {company}. Analyze filings in {file_list}.
      Return structured JSON following the schema in agents.md.
      Focus on: revenue trajectory, margins, cash flow, CEO credibility."

Task: "Run SENTIMENT agent for {company}. Analyze {podcast_count} podcasts,
      {twitter_count} Twitter accounts. Return structured JSON.
      Focus on: overall sentiment, notable speakers, bull/bear arguments."

Task: "Run INSIDER agent for {company}. Analyze insider data in {file_list}.
      Return structured JSON. Focus on: net direction, significant trades."

Task: "Run EXTERN_RESEARCH agent for {company}. Search for recent news,
      Reddit sentiment, analyst views, short interest.
      Focus on negative findings and bear case. Return structured JSON."
```

### Step 5: Collect Results

```python
# Collect and validate JSON outputs from all agents
agent_outputs = {}
failed_agents = []

for agent_name, result in results.items():
    try:
        # Parse JSON from agent output
        output = json.loads(result)
        agent_outputs[agent_name] = output
    except json.JSONDecodeError:
        failed_agents.append(agent_name)
        print(f"⚠️  {agent_name} agent failed to return valid JSON")

# Note data limitations if agents failed
if failed_agents:
    data_limitations = [f"{agent} analysis unavailable" for agent in failed_agents]
```

### Step 6: Run Risk Agent

Reference: `agents.md` - Agent 5: RISKER & BEAR CASE

```python
# Risk agent runs AFTER agents 1-4 complete
# It synthesizes their outputs to build the bear case

risk_prompt = f"""
## Task: Risk Synthesis & Bear Case

You are the devil's advocate for {company_query}.

### Input from Other Agents

**FUNDAMENTA**: {json.dumps(agent_outputs.get('fundamenta', {}), indent=2)}

**SENTIMENT**: {json.dumps(agent_outputs.get('sentiment', {}), indent=2)}

**INSIDER**: {json.dumps(agent_outputs.get('insider_agare', {}), indent=2)}

**EXTERN**: {json.dumps(agent_outputs.get('extern_research', {}), indent=2)}

### Your Mission

1. Aggregate all risks identified by other agents
2. Rank risks by probability and impact
3. Identify blind spots - what are we missing?
4. Construct worst case scenario
5. Calculate downside fair value

Be ruthless. Find every reason NOT to invest.
"""

# Run risk agent (via Task tool)
risk_output = run_task(risk_prompt)
agent_outputs['risker_bear'] = risk_output
```

### Step 7: Peer Comparison

```python
# Suggest peers based on company type and sector
def suggest_peers(company: str, fundamenta_output: dict) -> list[str]:
    """Suggest peer companies for comparison."""

    # Common peer groups by sector
    peer_groups = {
        'gaming': ['EVO', 'BETS-B', 'KNDG', 'LCFY', 'RUSH'],
        'bank': ['SEB-A', 'SWED-A', 'SHB-A', 'NDA-SE'],
        'fastighet': ['CAST', 'WALL-B', 'FABG', 'HEBA-B'],
        'industri': ['VOLV-B', 'SAND', 'ALFA', 'ASSA-B'],
        'tech': ['HM-B', 'SINCH', 'EMBRAC-B']
    }

    # Detect sector from fundamenta output or company characteristics
    # Return suggested peers

    return suggested_peers

# Display peers and ask for confirmation
suggested = suggest_peers(company_query, agent_outputs.get('fundamenta', {}))

print(f"\n📊 Suggested peers for comparison: {', '.join(suggested)}")
print("These will be used for relative valuation.")

# Allow user to modify
response = input("Accept peers? (y/modify/skip): ")
if response.lower() == 'y':
    peers = suggested
elif response.lower() == 'skip':
    peers = []
else:
    # User provides custom peers
    peers = input("Enter peers (comma-separated): ").split(',')
    peers = [p.strip() for p in peers]
```

### Step 8: Build Scenarios

Reference: `valuation.md`

```python
from references.valuation import calculate_multiples, build_scenarios

# Get financial data from fundamenta agent
fundamenta = agent_outputs.get('fundamenta', {})

# Extract key metrics
base_ebitda = fundamenta.get('cash_flow', {}).get('ebitda', 0)
net_debt = fundamenta.get('balance_sheet', {}).get('net_debt', 0)

# Determine appropriate multiple based on company type
# Gaming: 8-12x EV/EBITDA
# SaaS: 15-25x EV/Sales
# Bank: 0.8-1.2x P/B

company_type = detect_company_type(fundamenta)
base_multiple = get_sector_multiple(company_type)

# Get current price and shares
current_price = get_current_price(company_query)  # Via price API
shares = fundamenta.get('shares_outstanding', 0)

# Get risk score from risk agent output (runs before this step)
risk_output = agent_outputs.get('risker_bear', {})
risk_score = risk_output.get('overall_risk_score', {}).get('score', 5)  # Default 5 (medium)

# Build scenarios with risk-adjusted parameters
scenarios = build_scenarios(
    base_ebitda=base_ebitda,
    base_multiple=base_multiple,
    net_debt=net_debt,
    shares=shares,
    # Adjust based on risk assessment (lower risk = wider scenarios)
    bull_ebitda_adj=0.20 if risk_score < 5 else 0.15,
    bear_ebitda_adj=-0.20 if risk_score < 5 else -0.30
)

# Add key assumptions to each scenario
scenarios[0]['key_assumptions'] = ['Market share gains', 'Margin expansion']
scenarios[1]['key_assumptions'] = ['Steady state growth', 'Current margins']
scenarios[2]['key_assumptions'] = ['Regulatory headwinds', 'Margin pressure']
```

### Step 9: Calculate Fair Value

Reference: `valuation.md`

```python
from references.valuation import calculate_fair_value, generate_verdict

# Calculate weighted fair value
fv_result = calculate_fair_value(scenarios)
weighted_fv = fv_result['weighted_fair_value']

# Determine confidence based on data availability and consistency
def determine_confidence(inventory: dict, agent_outputs: dict) -> str:
    """Determine analysis confidence level."""
    mode = inventory['summary']['mode']
    failed_agents = len([a for a in ['fundamenta', 'sentiment', 'insider_agare']
                        if a not in agent_outputs])

    if mode == 'full' and failed_agents == 0:
        return 'high'
    elif mode == 'discovery' or failed_agents >= 2:
        return 'low'
    else:
        return 'medium'

confidence = determine_confidence(inventory, agent_outputs)
```

### Step 10: Generate Verdict

Reference: `valuation.md`

```python
# Extract key risks for verdict
risk_output = agent_outputs.get('risker_bear', {})
key_risks = [r['risk'] for r in risk_output.get('risk_ranking', [])[:5]]

# Generate verdict
verdict = generate_verdict(
    weighted_fv=weighted_fv,
    current_price=current_price,
    confidence=confidence,
    scenarios=scenarios,
    key_risks=key_risks
)

# Display verdict
from references.output import display_header, display_verdict

header = display_header(company_name, ticker, inventory)
verdict_display = display_verdict(
    company=company_name,
    ticker=ticker,
    weighted_fair_value=weighted_fv,
    current_price=current_price,
    verdict=verdict,
    scenarios=scenarios,
    key_risks=key_risks
)

print(header)
print(verdict_display)
```

### Step 11: Save Analysis

Reference: `output.md`

```python
from references.output import save_analysis
from datetime import datetime

# Compile complete analysis
analysis = {
    'ticker': ticker,
    'company': company_name,
    'date': datetime.now().strftime('%Y-%m-%d'),
    'weighted_fair_value': weighted_fv,
    'current_price': current_price,
    'verdict': verdict,
    'scenarios': scenarios,
    'data_sources': {
        'mode': inventory['summary']['mode'],
        'filings_count': sources.get('filings', {}).get('count', 0),
        'podcasts_count': sources.get('podcasts', {}).get('count', 0),
        'twitter_count': sources.get('twitter', {}).get('count', 0),
        'youtube_count': sources.get('youtube', {}).get('count', 0),
        'insider_count': sources.get('insider', {}).get('count', 0),
        'news_count': sources.get('news', {}).get('count', 0),
        'external_searches': agent_outputs.get('extern_research', {}).get('searches_performed', [])
    },
    'fundamenta': agent_outputs.get('fundamenta'),
    'sentiment': agent_outputs.get('sentiment'),
    'insider': agent_outputs.get('insider_agare'),
    'risks': agent_outputs.get('risker_bear'),
    'peers': {
        'peer_group': peers
    },
    'user_context': user_context,
    'metadata': {
        'data_limitations': data_limitations if failed_agents else []
    }
}

# Save to disk
saved_path = save_analysis(analysis)
print(f"\n✅ Analysis saved to: {saved_path}")
```

---

## Interactive Follow-ups

After presenting the verdict, allow the user to ask follow-up questions:

```python
# Interactive session
print("\n" + "=" * 60)
print("Analysis complete. You can ask follow-up questions:")
print("  - 'Tell me more about the bear case'")
print("  - 'What are the key risks?'")
print("  - 'Compare to peers'")
print("  - 'Show me the insider activity'")
print("  - 'Exit' to end")
print("=" * 60)

while True:
    follow_up = input("\nQuestion: ").strip()

    if follow_up.lower() in ['exit', 'quit', 'q']:
        break

    # Route to appropriate section
    if 'bear' in follow_up.lower() or 'risk' in follow_up.lower():
        # Show risk agent output in detail
        display_risks(agent_outputs.get('risker_bear', {}))

    elif 'insider' in follow_up.lower():
        # Show insider agent output
        display_insider(agent_outputs.get('insider_agare', {}))

    elif 'sentiment' in follow_up.lower() or 'podcast' in follow_up.lower():
        # Show sentiment agent output
        display_sentiment(agent_outputs.get('sentiment', {}))

    elif 'peer' in follow_up.lower() or 'competitor' in follow_up.lower():
        # Show peer comparison
        display_peers(peers, peer_comparison)

    elif 'fundamental' in follow_up.lower() or 'financial' in follow_up.lower():
        # Show fundamenta agent output
        display_fundamenta(agent_outputs.get('fundamenta', {}))

    else:
        # General question - use full context to answer
        answer_question(follow_up, analysis)
```

---

## Execution Diagram

```
User: /alpha BETS-B "överväger att öka"
                    |
                    v
            +---------------+
            | 1. Parse Input |
            +-------+-------+
                    |
                    v
            +---------------+
            | 2. Inventory   |
            |    Data        |
            +-------+-------+
                    |
                    v
            +---------------+
            | 3. Check Gaps  |
            |    (confirm)   |
            +-------+-------+
                    |
    +---------------+---------------+---------------+
    |               |               |               |
    v               v               v               v
+-------+       +-------+       +-------+       +-------+
|FUNDA- |       |SENTI- |       |INSIDER|       |EXTERN |
|MENTA  |       |MENT   |       |       |       |RESEARCH|
+---+---+       +---+---+       +---+---+       +---+---+
    |               |               |               |
    +---------------+---------------+---------------+
                    |
                    v
            +---------------+
            | 5. Collect     |
            |    Results     |
            +-------+-------+
                    |
                    v
            +---------------+
            | 6. Risk Agent  |
            |    (synth)     |
            +-------+-------+
                    |
                    v
            +---------------+
            | 7. Peer        |
            |    Confirm     |
            +-------+-------+
                    |
                    v
            +---------------+
            | 8. Build       |
            |    Scenarios   |
            +-------+-------+
                    |
                    v
            +---------------+
            | 9. Fair Value  |
            +-------+-------+
                    |
                    v
            +---------------+
            | 10. Verdict    |
            +-------+-------+
                    |
                    v
            +---------------+
            | 11. Save       |
            +-------+-------+
                    |
                    v
            +---------------+
            | Follow-ups     |
            +---------------+
```

---

## Agent Timing Table

| Agent | Depends On | Runs When | Typical Duration |
|-------|------------|-----------|------------------|
| FUNDAMENTA | None | Filings available | 30-60s |
| SENTIMENT | None | Podcasts/Twitter/YouTube available | 20-40s |
| INSIDER | None | Insider data available | 10-20s |
| EXTERN_RESEARCH | None | Always | 30-60s |
| RISKER | Agents 1-4 | After all above complete | 20-30s |
| SYNTHESIS | All agents | Final step | 10-20s |

**Parallel execution**: Agents 1-4 run simultaneously
**Sequential execution**: Risk agent and Synthesis wait for predecessors

---

## Error Handling

```python
def handle_agent_failure(agent_name: str, error: Exception) -> dict:
    """Handle agent failure gracefully."""
    return {
        'agent': agent_name,
        'status': 'failed',
        'error': str(error),
        'fallback': get_fallback_data(agent_name)
    }

def get_fallback_data(agent_name: str) -> dict:
    """Provide minimal fallback data for failed agents."""
    fallbacks = {
        'fundamenta': {'quality_score': None, 'summary': 'Data unavailable'},
        'sentiment': {'overall_sentiment': {'label': 'unknown'}, 'summary': 'Data unavailable'},
        'insider_agare': {'net_direction': {'direction': 'unknown'}, 'summary': 'Data unavailable'},
        'extern_research': {'thesis_impact': {'new_information': False}, 'summary': 'Search failed'}
    }
    return fallbacks.get(agent_name, {})
```

When agents fail:
1. Log the error
2. Continue with available data
3. Note limitation in final analysis
4. Reduce confidence level
5. Flag missing data in verdict display
