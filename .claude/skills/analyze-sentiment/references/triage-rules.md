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
