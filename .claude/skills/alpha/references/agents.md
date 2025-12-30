# Agent Definitions

Parallel agent architecture for comprehensive company analysis.

## Orchestrator Flow

```
                              +------------------+
                              |   ORCHESTRATOR   |
                              |  (inventory +    |
                              |   dispatch)      |
                              +--------+---------+
                                       |
           +---------------------------+---------------------------+
           |               |               |               |       |
           v               v               v               v       |
   +-------+-------+ +-----+-----+ +-------+-------+ +-----+-----+ |
   |  FUNDAMENTA   | | SENTIMENT | |INSIDER & AGARE| |  EXTERN   | |
   |   (Agent 1)   | | (Agent 2) | |   (Agent 3)   | | RESEARCH  | |
   |               | |           | |               | | (Agent 4) | |
   | - Filings     | | - Podcasts| | - FI data     | | - News    | |
   | - CEO letters | | - Twitter | | - Holdings    | | - Reddit  | |
   | - Metrics     | | - YouTube | | - Changes     | | - Placera | |
   +-------+-------+ +-----+-----+ +-------+-------+ +-----+-----+ |
           |               |               |               |       |
           +---------------+---------------+---------------+       |
                                       |                           |
                                       v                           |
                              +--------+--------+                  |
                              | RISKER & BEAR   |<-----------------+
                              |    (Agent 5)    |
                              |                 |
                              | - Devil's adv.  |
                              | - Risk synthesis|
                              | - Bear case     |
                              +---------+-------+
                                        |
                                        v
                              +---------+-------+
                              |   SYNTHESIS     |
                              |                 |
                              | - Fair value    |
                              | - Bull/Base/Bear|
                              | - Verdict       |
                              +-----------------+
```

## Execution Model

- **Agents 1-4**: Run in parallel (no dependencies)
- **Agent 5**: Waits for Agents 1-4 to complete
- **Synthesis**: Runs after all agents complete

---

## Agent 1: FUNDAMENTA

**Purpose**: Analyze financial reports, CEO letters, and company fundamentals.

**Input Sources**:
- `data/filings/analysis/{company}/*.json` - Parsed financial reports
- `data/filings/raw/{company}/*.pdf` - Original filings (if analysis missing)

**Prompt Template**:

```markdown
## Task: Fundamental Analysis

Analyze the financial fundamentals for {company_name} ({ticker}).

### Available Data

{filings_summary}

### Extract

1. **Revenue trajectory**: CAGR over available periods, acceleration/deceleration
2. **Margin profile**: Gross, EBIT, Net margins and trends
3. **Cash generation**: FCF, FCF/Revenue, FCF conversion rate
4. **Balance sheet**: Net debt/EBITDA, equity ratio, working capital
5. **CEO tone**: Confidence level, key themes, promise vs delivery
6. **Capital allocation**: Dividends, buybacks, M&A, capex priorities

### Focus Areas

- Compare CEO promises in older reports to actual outcomes
- Identify margin expansion/compression drivers
- Flag any accounting red flags or aggressive assumptions
- Note seasonality patterns if visible

### Output

Return structured JSON following the schema below.
```

**Output Schema**:

```json
{
  "agent": "fundamenta",
  "company": "string",
  "ticker": "string",
  "analysis_date": "YYYY-MM-DD",
  "data_coverage": {
    "reports_analyzed": 0,
    "period_start": "YYYY-MM-DD",
    "period_end": "YYYY-MM-DD"
  },
  "revenue": {
    "latest_annual": 0,
    "cagr_3y": 0.0,
    "cagr_5y": 0.0,
    "trend": "accelerating|stable|decelerating",
    "notes": "string"
  },
  "margins": {
    "gross_margin": 0.0,
    "gross_margin_trend": "expanding|stable|contracting",
    "ebit_margin": 0.0,
    "ebit_margin_trend": "expanding|stable|contracting",
    "net_margin": 0.0,
    "notes": "string"
  },
  "cash_flow": {
    "fcf_latest": 0,
    "fcf_margin": 0.0,
    "fcf_conversion": 0.0,
    "notes": "string"
  },
  "balance_sheet": {
    "net_debt": 0,
    "net_debt_ebitda": 0.0,
    "equity_ratio": 0.0,
    "health": "strong|adequate|weak|distressed",
    "notes": "string"
  },
  "ceo_analysis": {
    "tone": "confident|cautious|defensive|evasive",
    "key_themes": ["string"],
    "promises_tracked": [
      {
        "promise": "string",
        "made_date": "YYYY-MM-DD",
        "status": "delivered|partial|missed|pending",
        "notes": "string"
      }
    ],
    "credibility_score": "high|medium|low"
  },
  "capital_allocation": {
    "dividend_policy": "string",
    "buyback_activity": "active|occasional|none",
    "ma_appetite": "acquisitive|selective|none",
    "capex_intensity": "high|moderate|low",
    "notes": "string"
  },
  "red_flags": ["string"],
  "quality_score": {
    "score": 0,
    "max": 10,
    "rationale": "string"
  },
  "summary": "string"
}
```

---

## Agent 2: SENTIMENT

**Purpose**: Analyze mentions in podcasts, Twitter, and YouTube to gauge market sentiment.

**Input Sources**:
- `data/podcasts/analyses-v2/*.json` - Podcast mentions
- `data/twitter/analyses/*.json` - Twitter mentions
- `data/youtube/analyses/*.json` - YouTube mentions
- `data/podstock.db` - Historical recommendations with prices

**Prompt Template**:

```markdown
## Task: Sentiment Analysis

Analyze market sentiment for {company_name} ({ticker}) from media sources.

### Available Mentions

**Podcasts**: {podcast_count} episodes
{podcast_summary}

**Twitter**: {twitter_count} accounts
{twitter_summary}

**YouTube**: {youtube_count} videos
{youtube_summary}

### Extract

1. **Overall sentiment**: Weighted by source credibility and recency
2. **Sentiment trend**: Is opinion improving or deteriorating?
3. **Notable speakers**: Who has strong conviction (bull or bear)?
4. **Bull arguments**: Most compelling reasons to own
5. **Bear arguments**: Most compelling reasons to avoid
6. **Price context**: What prices were mentioned at, vs current price

### Weighting Guidelines

- Weight recent mentions (last 3 months) 2x older ones
- Weight high-conviction speakers higher
- Note if sentiment is consensus or contrarian

### Output

Return structured JSON following the schema below.
```

**Output Schema**:

```json
{
  "agent": "sentiment",
  "company": "string",
  "ticker": "string",
  "analysis_date": "YYYY-MM-DD",
  "data_coverage": {
    "podcasts_analyzed": 0,
    "twitter_accounts": 0,
    "youtube_videos": 0,
    "earliest_mention": "YYYY-MM-DD",
    "latest_mention": "YYYY-MM-DD"
  },
  "overall_sentiment": {
    "score": 0.0,
    "label": "very_bullish|bullish|neutral|bearish|very_bearish",
    "confidence": "high|medium|low"
  },
  "sentiment_trend": {
    "direction": "improving|stable|deteriorating",
    "notes": "string"
  },
  "notable_speakers": [
    {
      "name": "string",
      "source": "podcast|twitter|youtube",
      "stance": "bull|bear|neutral",
      "conviction": "high|medium|low",
      "key_argument": "string",
      "mention_date": "YYYY-MM-DD",
      "price_at_mention": 0.0
    }
  ],
  "bull_case_arguments": [
    {
      "argument": "string",
      "frequency": 0,
      "most_cited_by": "string"
    }
  ],
  "bear_case_arguments": [
    {
      "argument": "string",
      "frequency": 0,
      "most_cited_by": "string"
    }
  ],
  "price_context": {
    "mentions_with_prices": [
      {
        "date": "YYYY-MM-DD",
        "price_mentioned": 0.0,
        "action_recommended": "buy|sell|hold|watch",
        "speaker": "string"
      }
    ],
    "avg_buy_price_mentioned": 0.0,
    "avg_sell_price_mentioned": 0.0
  },
  "consensus_vs_contrarian": {
    "is_consensus": true,
    "notes": "string"
  },
  "summary": "string"
}
```

---

## Agent 3: INSIDER & AGARE

**Purpose**: Analyze insider transactions and ownership structure.

**Input Sources**:
- `data/insider/raw/{market}/*.json` - Raw insider transaction data
- `data/insider/reports/*.json` - Processed insider reports
- `data/insider/cache/*.json` - Cached lookups

**Prompt Template**:

```markdown
## Task: Insider & Ownership Analysis

Analyze insider activity and ownership for {company_name} ({ticker}).

### Available Data

{insider_summary}

### Extract

1. **Net direction**: Are insiders net buyers or sellers over 12 months?
2. **Significant transactions**: Large trades by key people (CEO, CFO, board)
3. **Cluster activity**: Multiple insiders trading same direction
4. **Price context**: At what prices did insiders buy/sell?
5. **Ownership concentration**: Major shareholders and changes

### Interpretation Guidelines

- CEO/CFO transactions weight more than board members
- Cluster buying is stronger signal than single insider
- Consider tax/exercise vs conviction-based trades
- Compare insider prices to current price

### Output

Return structured JSON following the schema below.
```

**Output Schema**:

```json
{
  "agent": "insider_agare",
  "company": "string",
  "ticker": "string",
  "analysis_date": "YYYY-MM-DD",
  "data_coverage": {
    "transactions_analyzed": 0,
    "period_start": "YYYY-MM-DD",
    "period_end": "YYYY-MM-DD"
  },
  "net_direction": {
    "direction": "net_buyer|net_seller|neutral",
    "net_value_sek": 0,
    "buy_count": 0,
    "sell_count": 0,
    "conviction": "strong|moderate|weak"
  },
  "significant_transactions": [
    {
      "date": "YYYY-MM-DD",
      "insider_name": "string",
      "role": "CEO|CFO|Board|Other",
      "transaction_type": "buy|sell|exercise|gift",
      "shares": 0,
      "price": 0.0,
      "value_sek": 0,
      "is_conviction_trade": true,
      "notes": "string"
    }
  ],
  "cluster_activity": {
    "detected": true,
    "direction": "buying|selling",
    "insiders_involved": 0,
    "period": "string",
    "notes": "string"
  },
  "price_context": {
    "avg_insider_buy_price": 0.0,
    "avg_insider_sell_price": 0.0,
    "current_price": 0.0,
    "current_vs_avg_buy": 0.0,
    "notes": "string"
  },
  "ownership_structure": {
    "top_holders": [
      {
        "name": "string",
        "ownership_pct": 0.0,
        "change_12m": 0.0,
        "type": "founder|institution|insider|other"
      }
    ],
    "insider_ownership_pct": 0.0,
    "institutional_ownership_pct": 0.0,
    "notes": "string"
  },
  "signal_strength": {
    "score": 0,
    "max": 10,
    "interpretation": "strong_buy_signal|buy_signal|neutral|sell_signal|strong_sell_signal"
  },
  "summary": "string"
}
```

---

## Agent 4: EXTERN RESEARCH

**Purpose**: Search external sources for news, sentiment, and contrarian viewpoints.

**Input Sources**:
- WebSearch tool for real-time searches
- WebFetch for specific URLs
- Focus on: news, Reddit, Placera, short reports, analyst downgrades

**Prompt Template**:

```markdown
## Task: External Research

Research external sources for {company_name} ({ticker}).

### Search Strategy

1. **News search**: "{company_name} aktie" - recent news
2. **Problem search**: "{company_name} problem OR risk OR varning" - issues
3. **Reddit search**: "site:reddit.com {company_name} OR {ticker}"
4. **Placera search**: "site:placera.se {company_name}"
5. **Short interest**: "{company_name} blankningar OR short"

### Focus Areas

- **Negative bias**: Actively seek bear case and risks as counterweight
- **Recent events**: Anything in last 30 days that changes thesis
- **Analyst views**: Downgrades, target cuts, sell recommendations
- **Legal/regulatory**: Lawsuits, investigations, regulatory issues
- **Competition**: New entrants, market share losses

### Do NOT Search

- Generic company descriptions
- Historical stock price charts
- Basic financial data (covered by FUNDAMENTA agent)

### Output

Return structured JSON following the schema below.
```

**Output Schema**:

```json
{
  "agent": "extern_research",
  "company": "string",
  "ticker": "string",
  "analysis_date": "YYYY-MM-DD",
  "searches_performed": [
    {
      "query": "string",
      "results_found": 0,
      "relevant_results": 0
    }
  ],
  "news_summary": {
    "recent_news_count": 0,
    "sentiment": "positive|mixed|negative",
    "key_headlines": [
      {
        "headline": "string",
        "source": "string",
        "date": "YYYY-MM-DD",
        "sentiment": "positive|neutral|negative",
        "relevance": "high|medium|low"
      }
    ]
  },
  "negative_findings": [
    {
      "category": "legal|regulatory|competitive|financial|operational|governance",
      "finding": "string",
      "source": "string",
      "severity": "critical|significant|moderate|minor",
      "date": "YYYY-MM-DD"
    }
  ],
  "analyst_sentiment": {
    "recent_changes": [
      {
        "analyst": "string",
        "action": "upgrade|downgrade|initiate|reiterate",
        "rating": "string",
        "target_price": 0.0,
        "date": "YYYY-MM-DD"
      }
    ],
    "consensus": "buy|hold|sell",
    "avg_target": 0.0
  },
  "short_interest": {
    "data_found": true,
    "short_pct": 0.0,
    "trend": "increasing|stable|decreasing",
    "notes": "string"
  },
  "reddit_sentiment": {
    "mentions_found": 0,
    "overall_sentiment": "bullish|neutral|bearish|mixed",
    "notable_posts": ["string"]
  },
  "competitive_threats": [
    {
      "threat": "string",
      "severity": "high|medium|low",
      "source": "string"
    }
  ],
  "thesis_impact": {
    "new_information": true,
    "changes_thesis": true,
    "direction": "positive|neutral|negative",
    "notes": "string"
  },
  "summary": "string"
}
```

---

## Agent 5: RISKER & BEAR CASE

**Purpose**: Devil's advocate - synthesize all risks and construct the bear case.

**Input Sources**:
- Output from Agents 1-4 (waits for completion)
- Focuses on risks, red flags, and reasons NOT to invest

**Prompt Template**:

```markdown
## Task: Risk Synthesis & Bear Case

You are the devil's advocate. Your job is to find every reason NOT to invest in {company_name} ({ticker}).

### Input from Other Agents

**FUNDAMENTA findings**:
{fundamenta_output}

**SENTIMENT findings**:
{sentiment_output}

**INSIDER findings**:
{insider_output}

**EXTERN findings**:
{extern_output}

### Your Mission

1. **Aggregate all risks** identified by other agents
2. **Rank risks** by probability and impact
3. **Identify blind spots** - what are we missing?
4. **Construct worst case** - what kills the investment thesis?
5. **Calculate downside** - fair value in bear scenario

### Be Ruthless

- Challenge bullish assumptions
- Find the "what could go wrong"
- Consider black swan events
- Look for concentration risks
- Question management credibility

### Output

Return structured JSON following the schema below.
```

**Output Schema**:

```json
{
  "agent": "risker_bear",
  "company": "string",
  "ticker": "string",
  "analysis_date": "YYYY-MM-DD",
  "risk_ranking": [
    {
      "rank": 1,
      "risk": "string",
      "category": "financial|operational|competitive|regulatory|governance|macro|black_swan",
      "probability": "high|medium|low",
      "impact": "critical|major|moderate|minor",
      "source_agent": "fundamenta|sentiment|insider|extern|synthesis",
      "mitigation": "string"
    }
  ],
  "red_flags": [
    {
      "flag": "string",
      "severity": "critical|warning|watch",
      "explanation": "string"
    }
  ],
  "blind_spots": [
    {
      "area": "string",
      "why_concerning": "string",
      "data_needed": "string"
    }
  ],
  "bear_case": {
    "thesis": "string",
    "key_assumptions": ["string"],
    "trigger_events": ["string"],
    "timeline": "string"
  },
  "worst_case_valuation": {
    "scenario": "string",
    "fair_value": 0.0,
    "downside_from_current": 0.0,
    "assumptions": ["string"]
  },
  "kill_the_thesis": {
    "single_biggest_risk": "string",
    "probability": "high|medium|low",
    "what_to_watch": "string"
  },
  "overall_risk_score": {
    "score": 0,
    "max": 10,
    "interpretation": "very_high_risk|high_risk|moderate_risk|low_risk|very_low_risk"
  },
  "summary": "string"
}
```

---

## Synthesis Prompt

**Purpose**: Combine all agent outputs into final valuation and recommendation.

**Prompt Template**:

```markdown
## Task: Final Synthesis & Valuation

Synthesize all research into a final valuation for {company_name} ({ticker}).

### Agent Outputs

**FUNDAMENTA**: {fundamenta_summary}
Quality Score: {quality_score}/10

**SENTIMENT**: {sentiment_summary}
Overall: {sentiment_label} (confidence: {sentiment_confidence})

**INSIDER**: {insider_summary}
Signal: {insider_signal}

**EXTERN**: {extern_summary}
Thesis Impact: {thesis_impact}

**RISKER**: {risker_summary}
Risk Score: {risk_score}/10

### Current Market Data

- Current price: {current_price} SEK
- Market cap: {market_cap} SEK
- P/E: {pe_ratio}
- EV/EBIT: {ev_ebit}

### Calculate

1. **Bull case fair value**: Optimistic but realistic scenario
2. **Base case fair value**: Most likely outcome
3. **Bear case fair value**: Pessimistic but plausible scenario
4. **Probability weights**: Bull/Base/Bear percentages
5. **Expected value**: Weighted fair value

### Determine Verdict

Based on expected value vs current price:
- **Strong Buy**: >40% upside with moderate risk
- **Buy**: >20% upside
- **Hold**: -10% to +20%
- **Sell**: >10% downside
- **Strong Sell**: >30% downside or critical risks

### Output

Return structured JSON following the schema below.
```

**Output Schema**:

```json
{
  "synthesis": true,
  "company": "string",
  "ticker": "string",
  "analysis_date": "YYYY-MM-DD",
  "current_price": 0.0,
  "valuation": {
    "bull_case": {
      "fair_value": 0.0,
      "upside_pct": 0.0,
      "key_assumptions": ["string"],
      "probability": 0.0
    },
    "base_case": {
      "fair_value": 0.0,
      "upside_pct": 0.0,
      "key_assumptions": ["string"],
      "probability": 0.0
    },
    "bear_case": {
      "fair_value": 0.0,
      "downside_pct": 0.0,
      "key_assumptions": ["string"],
      "probability": 0.0
    },
    "expected_value": 0.0,
    "expected_return_pct": 0.0
  },
  "quality_metrics": {
    "fundamental_score": 0,
    "sentiment_score": 0,
    "insider_signal": "string",
    "risk_score": 0,
    "data_completeness": 0.0
  },
  "verdict": {
    "recommendation": "strong_buy|buy|hold|sell|strong_sell",
    "conviction": "high|medium|low",
    "rationale": "string"
  },
  "key_points": {
    "bull_points": ["string"],
    "bear_points": ["string"],
    "watch_items": ["string"]
  },
  "position_guidance": {
    "suggested_sizing": "full|half|starter|avoid",
    "entry_zone": {
      "lower": 0.0,
      "upper": 0.0
    },
    "stop_loss": 0.0,
    "take_profit_targets": [0.0]
  },
  "data_limitations": ["string"],
  "next_catalyst": {
    "event": "string",
    "expected_date": "YYYY-MM-DD",
    "impact": "high|medium|low"
  },
  "summary": "string"
}
```

---

## Agent Communication

Agents communicate through structured JSON output. The orchestrator:

1. Dispatches Agents 1-4 in parallel using Task tool
2. Collects outputs and validates JSON
3. Passes all outputs to Agent 5
4. Passes all outputs to Synthesis
5. Returns final verdict to user

### Error Handling

If an agent fails:
- Log error and continue with available data
- Note missing data in `data_limitations` field
- Reduce conviction if key agent failed
