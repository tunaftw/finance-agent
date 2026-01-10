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
