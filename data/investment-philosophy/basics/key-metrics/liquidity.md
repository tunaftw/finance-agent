# Liquidity Metrics

## Quick Answer

Liquidity metrics measure a company's ability to pay short-term obligations. Good liquidity means the company can survive unexpected challenges; poor liquidity can lead to bankruptcy even for profitable companies.

---

## Current Ratio

### Definition

Can the company pay off current liabilities with current assets?

### Formula

```
Current Ratio = Current Assets / Current Liabilities
```

### Where to Find It

- Balance Sheet → Current Assets (Omsättningstillgångar)
- Balance Sheet → Current Liabilities (Kortfristiga skulder)

### Example

| Item | Amount |
|------|--------|
| Current Assets | 500M |
| Current Liabilities | 300M |
| **Current Ratio** | **1.67** |

### Interpretation

| Ratio | Meaning |
|-------|---------|
| > 2.0 | Very comfortable |
| 1.5 - 2.0 | Healthy |
| 1.0 - 1.5 | Adequate |
| < 1.0 | Concerning - More current liabilities than assets |

### Caveats

- Too high (> 3.0) may mean inefficient use of assets
- Inventory can be illiquid - check quick ratio too
- Industry norms vary

---

## Quick Ratio (Acid Test)

### Definition

Can the company pay obligations without selling inventory?

### Formula

```
Quick Ratio = (Current Assets - Inventory) / Current Liabilities

or

Quick Ratio = (Cash + Receivables) / Current Liabilities
```

### Why Exclude Inventory?

- Inventory may be hard to sell quickly
- May require discounts to liquidate
- Could be obsolete

### Example

| Item | Amount |
|------|--------|
| Current Assets | 500M |
| Inventory | (150M) |
| Quick Assets | 350M |
| Current Liabilities | 300M |
| **Quick Ratio** | **1.17** |

### Interpretation

| Ratio | Meaning |
|-------|---------|
| > 1.5 | Very strong |
| 1.0 - 1.5 | Healthy |
| 0.5 - 1.0 | May be OK for low-inventory businesses |
| < 0.5 | Concerning |

---

## Cash Ratio

### Definition

The most conservative - can they pay with just cash?

### Formula

```
Cash Ratio = Cash & Equivalents / Current Liabilities
```

### Example

| Item | Amount |
|------|--------|
| Cash & Equivalents | 150M |
| Current Liabilities | 300M |
| **Cash Ratio** | **0.5** |

### Interpretation

- > 1.0: Can cover all current liabilities with cash
- 0.5 - 1.0: Reasonable cash buffer
- < 0.5: Relies on collections or borrowing

### Context

Few companies maintain cash ratio > 1.0 (inefficient). Compare to peers.

---

## Working Capital

### Definition

The operating liquidity available after covering short-term obligations.

### Formula

```
Working Capital = Current Assets - Current Liabilities
```

### Example

| Item | Amount |
|------|--------|
| Current Assets | 500M |
| Current Liabilities | 300M |
| **Working Capital** | **200M** |

### Interpretation

- Positive: Has buffer for operations
- Negative: May struggle to pay bills
- Trend matters more than absolute number

### Working Capital Ratio

```
WC Ratio = Working Capital / Revenue

or

WC Days = (Working Capital / Revenue) × 365
```

---

## Net Working Capital (NWC)

### Definition

Operating working capital, excluding cash and debt.

### Formula

```
NWC = (Current Assets - Cash) - (Current Liabilities - Short-term Debt)

or

NWC = Receivables + Inventory - Payables
```

### Why It Matters

- Shows capital tied up in operations
- Funded by permanent capital (debt/equity)
- Growth requires working capital investment

---

## Working Capital Changes & Cash Flow

### The Relationship

Changes in working capital affect cash flow:

| Change | Cash Flow Impact |
|--------|------------------|
| Receivables ↑ | Cash ↓ (Sold but didn't collect) |
| Inventory ↑ | Cash ↓ (Bought but didn't sell) |
| Payables ↑ | Cash ↑ (Bought but didn't pay) |

### Example: WC Investment

If a company grows 20% and maintains same WC/Revenue ratio:

```
Current Revenue: 1,000M
Current WC: 200M (20% of revenue)
Next Year Revenue: 1,200M
Required WC: 240M
WC Investment Needed: 40M (cash outflow)
```

---

## Defensive Interval

### Definition

How many days can the company operate using only liquid assets?

### Formula

```
Defensive Interval = Quick Assets / Daily Operating Expenses

Where:
Daily Operating Expenses = (COGS + Operating Expenses) / 365
```

### Example

| Item | Calculation |
|------|-------------|
| Quick Assets | 350M |
| Annual Operating Expenses | 730M |
| Daily Expenses | 2M |
| **Defensive Interval** | **175 days** |

---

## Swedish/IFRS Notes

### Terminology

| English | Swedish |
|---------|---------|
| Current Assets | Omsättningstillgångar |
| Current Liabilities | Kortfristiga skulder |
| Working Capital | Rörelsekapital |
| Cash & Equivalents | Likvida medel |
| Accounts Receivable | Kundfordringar |
| Inventory | Varulager |
| Accounts Payable | Leverantörsskulder |

### Swedish Reports

- Often include "Likviditetsgrad" (liquidity ratio) in key metrics
- Working capital analysis in management report

---

## Industry Context

| Industry | Typical Current Ratio |
|----------|----------------------|
| Utilities | Lower (1.0-1.2) - stable cash flows |
| Retail | Moderate (1.2-1.8) - inventory-heavy |
| Tech/Software | Higher (2.0+) - asset-light |
| Manufacturing | Moderate (1.5-2.0) |

---

## Quick Reference

| Metric | Formula | Healthy | Concern |
|--------|---------|---------|---------|
| **Current Ratio** | CA / CL | > 1.5 | < 1.0 |
| **Quick Ratio** | (CA - Inv) / CL | > 1.0 | < 0.5 |
| **Cash Ratio** | Cash / CL | > 0.5 | < 0.2 |
| **Working Capital** | CA - CL | Positive | Negative |

---

## Analysis Checklist

- [ ] Is current ratio > 1.5?
- [ ] Is quick ratio > 1.0?
- [ ] Is working capital positive?
- [ ] What's the trend (improving or declining)?
- [ ] How does it compare to peers?
- [ ] Any seasonal patterns in WC?
- [ ] Can they cover short-term debt maturities?

---

## Red Flags

- [ ] Current ratio < 1.0
- [ ] Declining liquidity ratios
- [ ] Negative working capital (unless retail/subscription)
- [ ] Large upcoming debt maturities
- [ ] Drawing on credit lines
- [ ] Stretching payables significantly

---

## See Also

- [Balance Sheet](../financial-statements/balance-sheet.md) - Source of liquidity data
- [Cash Flow Metrics](cash-flow.md) - Cash generation
- [Leverage Metrics](leverage.md) - Debt obligations
- [Efficiency Metrics](efficiency.md) - Working capital efficiency
