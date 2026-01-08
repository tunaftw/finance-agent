# Cash Flow Metrics

## Quick Answer

Cash flow metrics tell you how much real cash a business generates. They're harder to manipulate than earnings and show whether a company can fund growth, pay dividends, and survive downturns.

---

## Free Cash Flow (FCF)

### Definition

Cash available to shareholders after maintaining and growing the business.

### Formula

```
Free Cash Flow = Operating Cash Flow - Capital Expenditures

FCF = OCF - CapEx
```

### Where to Find It

- **OCF**: Cash Flow Statement → "Cash from Operating Activities"
- **CapEx**: Cash Flow Statement → "Purchases of Property, Plant & Equipment" (negative number, make positive)

### Example

| Item | Amount |
|------|--------|
| Operating Cash Flow | 500M |
| CapEx | (150M) |
| **Free Cash Flow** | **350M** |

### What It Tells You

- **Positive FCF**: Business generates excess cash
- **Negative FCF**: Business consumes cash (may be OK if growing)
- **Growing FCF**: Improving cash generation

### Good Values

- Positive for mature companies
- FCF Margin (FCF/Revenue) > 10% is strong
- FCF growing faster than revenue = improving efficiency

### Red Flags

- [ ] Negative FCF for mature companies
- [ ] FCF declining while revenue grows
- [ ] CapEx << Depreciation (underinvesting to boost FCF)

---

## Owner Earnings (Buffett's Measure)

### Definition

Warren Buffett's preferred cash flow metric - represents true cash available to owners.

### Formula

```
Owner Earnings = Net Income
               + Depreciation & Amortization
               - Maintenance CapEx
               - Required Working Capital Increases
```

### The Challenge

"Maintenance CapEx" isn't disclosed. You must estimate:
- **Conservative**: Use all CapEx
- **Moderate**: Use depreciation as proxy
- **Aggressive**: Estimate maintenance vs. growth CapEx

### Simple Approximation

```
Owner Earnings ≈ Net Income + D&A - (CapEx × 0.7)
```

(Assuming 70% of CapEx is maintenance)

### Example

| Item | Amount |
|------|--------|
| Net Income | 100M |
| Depreciation | 30M |
| CapEx | (50M) |
| Maintenance CapEx (est. 70%) | (35M) |
| **Owner Earnings** | **95M** |

---

## Cash Conversion

### Definition

How efficiently a company converts accounting earnings into actual cash.

### Formula

```
Cash Conversion = Operating Cash Flow / Net Income
```

### What It Tells You

| Ratio | Interpretation |
|-------|----------------|
| > 100% | Excellent - More cash than earnings |
| 80-100% | Good - Normal conversion |
| 50-80% | Concerning - Investigate accruals |
| < 50% | Red flag - Earnings quality issue |

### Example

| Item | Amount |
|------|--------|
| Operating Cash Flow | 120M |
| Net Income | 100M |
| **Cash Conversion** | **120%** (Excellent) |

### Why It Matters

Companies can report profits without generating cash. Common causes:
- Receivables growing (sold but not collected)
- Inventory building (bought but not sold)
- Aggressive revenue recognition

### Red Flags

- [ ] Cash conversion < 80% consistently
- [ ] Declining trend in cash conversion
- [ ] Large gap between OCF and Net Income

---

## FCF Yield

### Definition

Free cash flow relative to market value - like a "cash earnings yield."

### Formula

```
FCF Yield = Free Cash Flow / Market Capitalization

or

FCF Yield = Free Cash Flow / Enterprise Value
```

### What It Tells You

- How much cash return you're getting per dollar invested
- Compare to bond yields and other stocks
- Higher = cheaper (all else equal)

### Good Values

| FCF Yield | Interpretation |
|-----------|----------------|
| > 10% | Very cheap (or risky) |
| 5-10% | Potentially undervalued |
| 3-5% | Fair value range |
| < 3% | Expensive or high-growth |

### Example

| Item | Amount |
|------|--------|
| Free Cash Flow | 500M |
| Market Cap | 5,000M |
| **FCF Yield** | **10%** |

---

## Cash Conversion Cycle (CCC)

### Definition

How many days it takes to convert inventory investments into cash from sales.

### Formula

```
CCC = DIO + DSO - DPO

Where:
DIO = Days Inventory Outstanding
DSO = Days Sales Outstanding
DPO = Days Payables Outstanding
```

### Component Formulas

```
DIO = (Inventory / COGS) × 365
DSO = (Receivables / Revenue) × 365
DPO = (Payables / COGS) × 365
```

### What It Tells You

- **Lower is better** - Cash comes back faster
- **Negative** - Amazing! (Amazon, Dell) - Collect before paying suppliers

### Example

| Metric | Days |
|--------|------|
| DIO | 45 |
| DSO | 35 |
| DPO | 40 |
| **CCC** | **40 days** |

### Red Flags

- [ ] CCC increasing = Cash tied up longer
- [ ] DSO increasing faster than revenue growth
- [ ] DIO increasing = Inventory problems

---

## CAPEX Analysis

### Maintenance vs. Growth CapEx

```
Total CapEx = Maintenance CapEx + Growth CapEx
```

**Maintenance CapEx**: Keeps current operations running
**Growth CapEx**: Expands capacity

### Rule of Thumb

```
If CapEx ≈ Depreciation → Mostly maintenance
If CapEx >> Depreciation → Includes growth investment
If CapEx << Depreciation → Underinvesting (concern)
```

### CapEx Intensity

```
CapEx Intensity = CapEx / Revenue
```

| Intensity | Industry Type |
|-----------|---------------|
| < 3% | Asset-light (software, services) |
| 3-7% | Moderate (retail, manufacturing) |
| > 7% | Capital-intensive (utilities, telecom) |

---

## Swedish/IFRS Notes

### Terminology

| English | Swedish |
|---------|---------|
| Free Cash Flow | Fritt kassaflöde |
| Operating Cash Flow | Kassaflöde från löpande verksamhet |
| Capital Expenditure | Investeringar i anläggningstillgångar |
| Working Capital | Rörelsekapital |

### IFRS 16 Impact

Under IFRS 16, lease payments are split:
- Interest portion → Operating (or Financing)
- Principal portion → Financing

This **increases Operating Cash Flow** compared to old rules. Be careful comparing to historical or US peers.

---

## Quick Reference

| Metric | Formula | Good Value |
|--------|---------|------------|
| **FCF** | OCF - CapEx | Positive, growing |
| **FCF Margin** | FCF / Revenue | > 10% |
| **Cash Conversion** | OCF / Net Income | > 100% |
| **FCF Yield** | FCF / Market Cap | > 5% |
| **CCC** | DIO + DSO - DPO | Lower is better |

---

## See Also

- [Cash Flow Statement](../financial-statements/cash-flow-statement.md)
- [Efficiency Metrics](efficiency.md) - DSO, DIO, DPO details
- [Profitability Metrics](profitability.md) - Margins and returns
