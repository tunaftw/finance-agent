# Piotroski F-Score

## Quick Reference

- **Creator**: Joseph Piotroski, Stanford GSB (2000)
- **Purpose**: Score financial health of value stocks using 9 binary signals
- **Alpha Generated**: +7.5% annual return vs simple value basket

---

## Overview

The Piotroski F-Score is a quantitative scoring system that uses 9 accounting-based signals to assess the financial strength of a company. It was designed to separate strong value stocks from "value traps" - cheap stocks that are cheap for good reason.

Published in the 2000 paper "Value Investing: The Use of Historical Financial Statement Information to Separate Winners from Losers," Piotroski demonstrated that applying this score to high book-to-market (value) stocks generated significant excess returns.

The beauty of the F-Score is its simplicity: each signal is binary (0 or 1), and the total score ranges from 0 (weakest) to 9 (strongest). Stocks scoring 8-9 historically outperformed, while those scoring 0-2 underperformed.

---

## The 9 Signals

### Profitability (4 points)

| # | Signal | Score = 1 if... | Rationale |
|---|--------|-----------------|-----------|
| 1 | **ROA** | Net Income > 0 | Basic profitability |
| 2 | **CFO** | Operating Cash Flow > 0 | Cash generation |
| 3 | **ΔROA** | ROA this year > ROA last year | Improving profitability |
| 4 | **Accruals** | CFO > Net Income | Earnings quality (cash-backed) |

### Leverage/Liquidity (3 points)

| # | Signal | Score = 1 if... | Rationale |
|---|--------|-----------------|-----------|
| 5 | **ΔLeverage** | Long-term Debt/Assets decreased | Reduced financial risk |
| 6 | **ΔLiquidity** | Current Ratio increased | Improved short-term solvency |
| 7 | **No Dilution** | No new shares issued | No equity dilution |

### Operating Efficiency (2 points)

| # | Signal | Score = 1 if... | Rationale |
|---|--------|-----------------|-----------|
| 8 | **ΔMargin** | Gross Margin increased | Pricing power/efficiency |
| 9 | **ΔTurnover** | Asset Turnover increased | Better capital utilization |

---

## Calculation Formulas

```python
def piotroski_f_score(current, prior):
    """
    Calculate Piotroski F-Score from financial data.

    Args:
        current: dict with current period financials
        prior: dict with prior period financials

    Returns:
        int: F-Score (0-9)
    """
    score = 0

    # 1. ROA positive
    roa_current = current['net_income'] / current['total_assets']
    if roa_current > 0:
        score += 1

    # 2. Operating cash flow positive
    if current['operating_cash_flow'] > 0:
        score += 1

    # 3. ROA improvement
    roa_prior = prior['net_income'] / prior['total_assets']
    if roa_current > roa_prior:
        score += 1

    # 4. Accruals (CFO > Net Income = quality earnings)
    if current['operating_cash_flow'] > current['net_income']:
        score += 1

    # 5. Leverage decrease
    leverage_current = current['long_term_debt'] / current['total_assets']
    leverage_prior = prior['long_term_debt'] / prior['total_assets']
    if leverage_current < leverage_prior:
        score += 1

    # 6. Current ratio improvement
    cr_current = current['current_assets'] / current['current_liabilities']
    cr_prior = prior['current_assets'] / prior['current_liabilities']
    if cr_current > cr_prior:
        score += 1

    # 7. No share dilution
    if current['shares_outstanding'] <= prior['shares_outstanding']:
        score += 1

    # 8. Gross margin improvement
    gm_current = current['gross_profit'] / current['revenue']
    gm_prior = prior['gross_profit'] / prior['revenue']
    if gm_current > gm_prior:
        score += 1

    # 9. Asset turnover improvement
    at_current = current['revenue'] / current['total_assets']
    at_prior = prior['revenue'] / prior['total_assets']
    if at_current > at_prior:
        score += 1

    return score
```

---

## Interpretation

| Score | Interpretation | Action |
|-------|----------------|--------|
| 8-9 | Strong financials | Buy candidates (among value stocks) |
| 5-7 | Average | Hold/investigate further |
| 2-4 | Weak | Caution required |
| 0-1 | Very weak | Avoid or short candidates |

---

## Research Evidence

### Original Study (2000)

- Universe: High book-to-market stocks (value quintile)
- Period: 1976-1996
- **Finding**: High F-Score (8-9) stocks earned 13.4% annually vs 5.9% for all value stocks
- Long high F-Score + Short low F-Score = 23% annual return

### Subsequent Validation

- **Amor-Tapia & Tascon (2016)**: F-Score survived out-of-sample testing in European markets
- **Alpha Architect (2024)**: Combining F-Score with other value factors improves returns
- **Neural F-Score Research**: ML improvements add additional alpha

---

## Limitations

1. **Backward-looking**: Uses last year's data, not forward projections
2. **Sector agnostic**: Doesn't account for industry-specific norms
3. **Binary simplification**: Loses nuance (barely positive vs strongly positive both = 1)
4. **Works best for value stocks**: Originally designed for high book-to-market companies

---

## Implementation in Our System

### Integration with Filing Analysis

Add to `src/podstock/filings/analysis/deep_analysis.py`:

```python
PIOTROSKI_EXTRACTION_PROMPT = """Extract data needed for Piotroski F-Score calculation.

From the financial statements, extract:
1. Net Income (current and prior year)
2. Total Assets (current and prior year)
3. Operating Cash Flow (current and prior year)
4. Long-term Debt (current and prior year)
5. Current Assets (current and prior year)
6. Current Liabilities (current and prior year)
7. Shares Outstanding (current and prior year)
8. Gross Profit (current and prior year)
9. Revenue (current and prior year)

Return as JSON with current and prior periods.
"""
```

### Output Addition

Add to analysis JSON output:
```json
{
  "quantitative_scores": {
    "piotroski_f_score": 7,
    "f_score_breakdown": {
      "roa_positive": 1,
      "cfo_positive": 1,
      "roa_improving": 0,
      "accruals_quality": 1,
      "leverage_decreasing": 1,
      "liquidity_improving": 1,
      "no_dilution": 1,
      "margin_improving": 0,
      "turnover_improving": 1
    }
  }
}
```

---

## Sources

- [Piotroski Original Paper (2000)](https://www.chicagobooth.edu/~/media/fe874ee65f624aaebd0166b1974fd74d.pdf)
- [Piotroski F-Score - Wikipedia](https://en.wikipedia.org/wiki/Piotroski_F-score)
- [Alpha Architect: Improving F-Score](https://alphaarchitect.com/value-investing-research-simple-methods-to-improve-the-piotroski-f-score/)
- [StableBread: F-Score Guide](https://stablebread.com/piotroski-f-score/)
