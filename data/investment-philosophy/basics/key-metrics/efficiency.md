# Efficiency Metrics

## Quick Answer

Efficiency metrics (turnover ratios) measure how well a company uses its assets and manages its working capital. They reveal operational effectiveness and can signal problems before they hit the income statement.

---

## Days Sales Outstanding (DSO)

### Definition

Average time to collect payment from customers.

### Formula

```
DSO = (Accounts Receivable / Revenue) × 365

or for a quarter:
DSO = (Accounts Receivable / Quarterly Revenue) × 91
```

### Where to Find It

- **Receivables**: Balance Sheet → Accounts Receivable (Kundfordringar)
- **Revenue**: Income Statement → Net Revenue

### Example

| Item | Amount |
|------|--------|
| Accounts Receivable | 200M |
| Annual Revenue | 1,200M |
| **DSO** | **61 days** |

### Interpretation

- Lower is better - faster collection
- Compare to payment terms (e.g., Net 30)
- Industry norms vary significantly

| DSO | Signal |
|-----|--------|
| < 30 days | Excellent collection |
| 30-45 days | Good |
| 45-60 days | Average |
| > 60 days | May indicate problems |

### Red Flags

- [ ] DSO increasing while revenue flat
- [ ] DSO much higher than industry peers
- [ ] DSO higher than stated payment terms

---

## Days Inventory Outstanding (DIO)

### Definition

Average time inventory sits before being sold.

### Formula

```
DIO = (Inventory / COGS) × 365
```

### Where to Find It

- **Inventory**: Balance Sheet → Inventory (Varulager)
- **COGS**: Income Statement → Cost of Goods Sold

### Example

| Item | Amount |
|------|--------|
| Inventory | 150M |
| Annual COGS | 600M |
| **DIO** | **91 days** |

### Interpretation

- Lower is generally better - faster turnover
- But too low might mean stockouts
- Industry-dependent

| Industry | Typical DIO |
|----------|-------------|
| Grocery | 15-30 days |
| Apparel | 60-120 days |
| Industrial | 45-90 days |
| Tech Hardware | 30-60 days |

### Red Flags

- [ ] DIO increasing = Demand problems
- [ ] DIO higher than shelf life
- [ ] Inventory write-offs coming

---

## Days Payables Outstanding (DPO)

### Definition

Average time to pay suppliers.

### Formula

```
DPO = (Accounts Payable / COGS) × 365
```

### Where to Find It

- **Payables**: Balance Sheet → Accounts Payable (Leverantörsskulder)
- **COGS**: Income Statement

### Example

| Item | Amount |
|------|--------|
| Accounts Payable | 100M |
| Annual COGS | 600M |
| **DPO** | **61 days** |

### Interpretation

- Higher DPO = More supplier financing (good for cash)
- But very high may strain supplier relationships
- Balance with DSO and DIO

---

## Cash Conversion Cycle (CCC)

### Definition

Total days from paying for inventory to collecting from customers.

### Formula

```
CCC = DIO + DSO - DPO
```

### Example

| Metric | Days |
|--------|------|
| DIO | 91 |
| DSO | 61 |
| DPO | 61 |
| **CCC** | **91 days** |

### Interpretation

- Lower is better - less working capital needed
- Negative CCC = Amazing (collect before paying)
- Growing CCC = More cash tied up

### Famous Negative CCCs

- **Amazon**: Collects from customers before paying suppliers
- **Dell (historically)**: Made-to-order with fast collection

---

## Asset Turnover

### Definition

How efficiently assets generate revenue.

### Formula

```
Asset Turnover = Revenue / Average Total Assets
```

### Example

| Item | Amount |
|------|--------|
| Revenue | 1,200M |
| Avg Total Assets | 2,400M |
| **Asset Turnover** | **0.5x** |

### Interpretation

- Higher = More efficient asset use
- Asset-light businesses: > 1.0
- Capital-intensive: Often < 0.5

| Business Type | Typical Turnover |
|---------------|------------------|
| Software/Services | 0.5-2.0 |
| Retail | 1.5-3.0 |
| Manufacturing | 0.5-1.5 |
| Utilities | 0.2-0.4 |

---

## Fixed Asset Turnover

### Definition

How efficiently fixed assets generate revenue.

### Formula

```
Fixed Asset Turnover = Revenue / Average Net PP&E
```

### Example

| Item | Amount |
|------|--------|
| Revenue | 1,200M |
| Avg Net PP&E | 600M |
| **Fixed Asset Turnover** | **2.0x** |

### What It Tells You

- Capacity utilization
- Manufacturing efficiency
- Whether CapEx is paying off

---

## Inventory Turnover

### Definition

How many times inventory is sold and replaced per year.

### Formula

```
Inventory Turnover = COGS / Average Inventory

or

Inventory Turnover = 365 / DIO
```

### Example

| Item | Amount |
|------|--------|
| COGS | 600M |
| Avg Inventory | 150M |
| **Inventory Turnover** | **4.0x** |

### Interpretation

- Higher = Faster-moving inventory
- But too high may mean stockouts
- Compare within industry

---

## Receivables Turnover

### Definition

How many times receivables are collected per year.

### Formula

```
Receivables Turnover = Revenue / Average Accounts Receivable

or

Receivables Turnover = 365 / DSO
```

### Example

| Item | Amount |
|------|--------|
| Revenue | 1,200M |
| Avg Receivables | 200M |
| **Receivables Turnover** | **6.0x** |

### Interpretation

- Higher = Faster collection
- Compare to industry and payment terms

---

## Swedish/IFRS Notes

### Terminology

| English | Swedish |
|---------|---------|
| Days Sales Outstanding | Kundfordringar i dagar |
| Days Inventory Outstanding | Varulager i dagar |
| Days Payables Outstanding | Leverantörsskulder i dagar |
| Asset Turnover | Kapitalomsättning |
| Inventory Turnover | Lageromsättning |

### Swedish Reports

Often include:
- "Omsättningshastighet" (turnover speed) metrics
- Working capital analysis in management report

---

## Quick Reference

| Metric | Formula | Lower is Better? |
|--------|---------|------------------|
| **DSO** | (AR / Revenue) × 365 | Yes |
| **DIO** | (Inv / COGS) × 365 | Yes (usually) |
| **DPO** | (AP / COGS) × 365 | Higher = more financing |
| **CCC** | DIO + DSO - DPO | Yes |
| **Asset Turnover** | Revenue / Assets | Higher is better |
| **Inventory Turnover** | COGS / Inventory | Higher is better |

---

## Analysis Checklist

- [ ] Calculate DSO, DIO, DPO and CCC
- [ ] Compare to prior periods (trend)
- [ ] Compare to industry peers
- [ ] Is DSO increasing without revenue growth?
- [ ] Is inventory building up?
- [ ] Is the company stretching payables?
- [ ] What's the overall CCC trend?

---

## Red Flags Summary

| Metric | Red Flag |
|--------|----------|
| DSO | Increasing faster than revenue |
| DIO | Increasing (demand problems) |
| DPO | Suddenly increasing much (cash problems) |
| CCC | Lengthening trend |
| Asset Turnover | Declining (overcapacity) |

---

## See Also

- [Cash Flow Metrics](cash-flow.md) - Cash conversion cycle impact
- [Liquidity Metrics](liquidity.md) - Working capital analysis
- [Balance Sheet](../financial-statements/balance-sheet.md) - Source data
