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
