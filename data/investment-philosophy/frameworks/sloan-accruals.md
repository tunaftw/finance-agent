# Sloan Accruals Anomaly

## Quick Reference

- **Creator**: Richard Sloan (1996)
- **Purpose**: Measure earnings quality via accruals ratio
- **Alpha Generated**: +10.4% CAGR in long/short strategy

---

## Overview

The Sloan Accruals Anomaly demonstrates that companies with high accruals (earnings not backed by cash flow) tend to underperform, while companies with low accruals (cash-backed earnings) tend to outperform.

**Core Insight**: Cash is truth. Accounting earnings can be manipulated, but cash flow is harder to fake.

---

## The Formula

### Basic Accruals Ratio

```
Accruals Ratio = (Net Income - Operating Cash Flow) / Total Assets
```

### Alternative Calculation (Balance Sheet Method)

```
Accruals = ΔCurrent Assets - ΔCash - ΔCurrent Liabilities + ΔShort-term Debt - D&A
Accruals Ratio = Accruals / Average Total Assets
```

---

## Interpretation

| Accruals Ratio | Earnings Quality | Signal |
|----------------|------------------|--------|
| **< 0.05** | High | Cash-backed earnings; reliable |
| **0.05 - 0.10** | Medium | Acceptable but monitor |
| **> 0.10** | Low | Earnings not supported by cash; investigate |
| **Negative** | Very High | Cash flow exceeds accounting earnings |

---

## Why It Works

### 1. Accruals Reverse

High accruals today must reverse in future periods:
- Aggressive revenue recognition → future revenue shortfall
- Deferred expenses → future expense recognition
- Inventory build-up → future write-downs

### 2. Management Incentives

Managers have incentives to inflate short-term earnings:
- Bonus targets tied to earnings
- Stock price maintenance
- Debt covenant compliance

### 3. Market Mispricing

Investors focus on earnings, not cash flow:
- Analysts forecast EPS, not OCF
- Headlines report earnings beats/misses
- Cash flow statement is less scrutinized

---

## Implementation

### Step 1: Gather Data

From the most recent annual report:
- Net Income (Resultat efter skatt)
- Operating Cash Flow (Kassaflöde från löpande verksamhet)
- Total Assets (Summa tillgångar)

### Step 2: Calculate

```python
def calculate_accruals_ratio(net_income, ocf, total_assets):
    """
    Calculate Sloan accruals ratio.

    Args:
        net_income: Net income from income statement
        ocf: Operating cash flow from cash flow statement
        total_assets: Total assets from balance sheet

    Returns:
        Accruals ratio and quality grade
    """
    accruals = net_income - ocf
    ratio = accruals / total_assets

    if ratio < 0.05:
        grade = "high"
    elif ratio < 0.10:
        grade = "medium"
    else:
        grade = "low"

    return {
        "accruals_ratio": round(ratio, 4),
        "quality_grade": grade,
        "accruals_amount": accruals
    }
```

### Step 3: Interpret

| Finding | Action |
|---------|--------|
| Ratio < 0: Negative accruals | Cash flow exceeds earnings - very good quality |
| Ratio 0-0.05 | High quality - earnings reliable |
| Ratio 0.05-0.10 | Medium quality - acceptable |
| Ratio > 0.10 | Low quality - dig deeper into causes |
| Ratio > 0.15 | Warning - significant manipulation risk |

---

## Red Flags When Accruals Are High

If accruals ratio > 0.10, investigate:

1. **Revenue Recognition**
   - Is AR growing faster than revenue?
   - Bill-and-hold arrangements?
   - Channel stuffing at quarter end?

2. **Expense Capitalization**
   - R&D or software development capitalized?
   - Extended depreciation lives?
   - Deferred costs on balance sheet?

3. **Working Capital Changes**
   - Large inventory build-up?
   - Prepaid expenses increasing?
   - Accrued liabilities decreasing?

4. **One-Time Items**
   - Gains from asset sales?
   - Reserve releases?
   - Pension gains?

---

## Combining with Other Metrics

### Accruals + Piotroski F-Score

The Piotroski F-Score includes an accruals signal (OCF > Net Income). Use both:

| Accruals Ratio | F-Score Signal |
|----------------|----------------|
| < 0 | OCF > NI: TRUE (+1 point) |
| > 0 | OCF > NI: FALSE (+0 points) |

### Accruals + Revenue Quality

Check DSO (Days Sales Outstanding) alongside accruals:

| Pattern | Interpretation |
|---------|----------------|
| High accruals + Rising DSO | Double red flag - revenue quality issues |
| Low accruals + Stable DSO | Good quality earnings |
| High accruals + Stable DSO | Expense timing issues (less concerning) |

---

## Historical Performance

From Sloan's 1996 research:

- **Long portfolio** (low accruals): +4.4% annual alpha
- **Short portfolio** (high accruals): -5.5% annual alpha
- **Long/Short spread**: +10.4% annually

The effect persists despite being known since 1996, likely because:
- Institutional constraints on shorting
- Career risk for active managers
- Persistent investor focus on earnings

---

## Swedish/IFRS Notes

### Terminology

| English | Swedish |
|---------|---------|
| Net Income | Årets resultat |
| Operating Cash Flow | Kassaflöde från löpande verksamhet |
| Total Assets | Summa tillgångar |
| Accruals | Periodiseringar |

### IFRS Considerations

- IFRS allows more R&D capitalization than US GAAP
- Check "Immateriella tillgångar" (intangibles) for capitalized development
- IFRS lease accounting (IFRS 16) affects OCF classification

---

## Example Calculation

**Company: Getinge (2024)**

| Item | Amount (MSEK) |
|------|---------------|
| Net Income | 2,850 |
| Operating Cash Flow | 3,200 |
| Total Assets | 58,000 |

```
Accruals = 2,850 - 3,200 = -350 MSEK
Accruals Ratio = -350 / 58,000 = -0.006
```

**Result**: Negative accruals ratio (-0.6%) indicates excellent earnings quality - cash flow exceeds accounting earnings.

---

## Integration with Filing Analysis

When analyzing filings, include accruals assessment:

```json
{
  "earnings_quality": {
    "accruals_ratio": -0.006,
    "quality_grade": "high",
    "ocf_to_ni_ratio": 1.12,
    "interpretation": "Cash-backed earnings - reliable"
  }
}
```

---

## Checklist

- [ ] Calculate accruals ratio
- [ ] Compare to prior year (trend)
- [ ] Check if ratio > 0.10 (investigate)
- [ ] Verify OCF-to-NI ratio
- [ ] Look for one-time items
- [ ] Check DSO trend (revenue quality)
- [ ] Review capitalized costs

---

## See Also

- [Piotroski F-Score](piotroski-f-score.md) - Includes accruals signal
- [Schilit 7 Shenanigans](schilit-7-shenanigans.md) - Fraud detection
- [Cash Flow Metrics](../basics/key-metrics/cash-flow.md) - OCF calculation
- [Red Flags Checklist](../techniques/red-flags-checklist.md) - Warning signs

---

## Sources

- Sloan, R. (1996). "Do Stock Prices Fully Reflect Information in Accruals and Cash Flows about Future Earnings?" *The Accounting Review*.
- Collins, D. & Hribar, P. (2000). "Earnings-based and accrual-based market anomalies: one effect or two?"
