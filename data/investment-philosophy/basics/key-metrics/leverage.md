# Leverage & Debt Metrics

## Quick Answer

Leverage metrics show how much debt a company uses and whether it can service that debt. Too much leverage increases risk; too little might mean missed opportunities.

---

## Debt-to-Equity (D/E)

### Definition

Total debt relative to shareholder equity.

### Formula

```
Debt-to-Equity = Total Debt / Shareholders' Equity
```

### Where to Find It

- **Total Debt**: Balance Sheet → Short-term debt + Long-term debt
- **Equity**: Balance Sheet → Shareholders' Equity (Eget kapital)

### Example

| Item | Amount |
|------|--------|
| Short-term Debt | 200M |
| Long-term Debt | 800M |
| **Total Debt** | **1,000M** |
| Shareholders' Equity | 2,000M |
| **Debt-to-Equity** | **0.5** |

### Interpretation

| D/E Ratio | Interpretation |
|-----------|----------------|
| < 0.5 | Conservative - Low risk |
| 0.5 - 1.0 | Moderate - Typical |
| 1.0 - 2.0 | Elevated - Higher risk |
| > 2.0 | High leverage - Significant risk |

### Industry Context

- **Utilities**: Often 1.5-2.0 (stable cash flows support debt)
- **Tech**: Often < 0.5 (asset-light)
- **Banks**: Much higher (different rules)

---

## Debt-to-EBITDA

### Definition

How many years of EBITDA it would take to pay off all debt.

### Formula

```
Debt-to-EBITDA = Total Debt / EBITDA
```

Where:
```
EBITDA = Operating Income + Depreciation + Amortization
```

### Example

| Item | Amount |
|------|--------|
| Total Debt | 1,000M |
| EBITDA | 400M |
| **Debt/EBITDA** | **2.5x** |

### Interpretation

| Ratio | Interpretation |
|-------|----------------|
| < 2x | Conservative |
| 2-3x | Moderate |
| 3-4x | Elevated |
| > 4x | High (often triggers loan covenants) |

### Why It Matters

- Loan covenants often set maximum Debt/EBITDA (e.g., < 4x)
- PE firms often push this to 5-7x (risky)
- Check trends - rising ratio is concerning

---

## Net Debt

### Definition

Total debt minus cash - what you'd actually need to pay off.

### Formula

```
Net Debt = Total Debt - Cash & Equivalents
```

### Example

| Item | Amount |
|------|--------|
| Total Debt | 1,000M |
| Cash | 300M |
| **Net Debt** | **700M** |

### Special Cases

- **Negative Net Debt**: More cash than debt (net cash position) - Very strong
- **Net Debt / EBITDA**: Often more meaningful than gross debt

---

## Interest Coverage

### Definition

How many times the company can pay its interest expense from operating profits.

### Formula

```
Interest Coverage = EBIT / Interest Expense

or

Interest Coverage = EBITDA / Interest Expense
```

### Where to Find It

- **EBIT**: Income Statement → Operating Income
- **Interest Expense**: Income Statement → Interest Expense (Räntekostnader)

### Example

| Item | Amount |
|------|--------|
| EBIT | 300M |
| Interest Expense | 50M |
| **Interest Coverage** | **6.0x** |

### Interpretation

| Coverage | Interpretation |
|----------|----------------|
| > 10x | Very safe |
| 5-10x | Comfortable |
| 3-5x | Adequate |
| 2-3x | Concerning |
| < 2x | Distressed - Default risk |

### Red Flag

If interest coverage is declining, investigate:
- Rising debt levels?
- Falling operating income?
- Rising interest rates on variable debt?

---

## Debt-to-Assets

### Definition

What portion of assets is financed by debt.

### Formula

```
Debt-to-Assets = Total Debt / Total Assets
```

### Example

| Item | Amount |
|------|--------|
| Total Debt | 1,000M |
| Total Assets | 5,000M |
| **Debt/Assets** | **20%** |

### Interpretation

- Lower is more conservative
- 20-40% typical for industrials
- Compare within industry

---

## Debt Maturity Profile

### What to Check

Look at footnotes for debt maturity schedule:

```
Year 1: 100M due
Year 2: 150M due
Year 3: 200M due
Year 4: 50M due
Year 5+: 500M due
```

### Red Flags

- [ ] Large maturities in next 1-2 years
- [ ] "Wall of debt" coming due
- [ ] Refinancing risk if credit tightens

---

## Covenant Compliance

### What Are Covenants?

Loan agreements often require:
- Maximum Debt/EBITDA (e.g., < 4.0x)
- Minimum Interest Coverage (e.g., > 3.0x)
- Maximum leverage ratio

### Where to Find

- 10-K footnotes on debt
- Credit agreement summaries
- Management discussion of compliance

### Red Flags

- [ ] Company "close to" covenant limits
- [ ] Covenant waivers or amendments
- [ ] Declining cushion to covenant thresholds

---

## Lease Obligations (IFRS 16)

### Why It Matters

Since 2019 (IFRS 16), leases are on the balance sheet:
- Right-of-use asset
- Lease liability

### Adjusted Metrics

```
Adjusted Debt = Total Debt + Lease Liabilities
```

For comparison with historical or US companies, you may need to add back operating leases.

---

## Swedish/IFRS Notes

### Terminology

| English | Swedish |
|---------|---------|
| Total Debt | Totala räntebärande skulder |
| Long-term Debt | Långfristiga skulder |
| Short-term Debt | Kortfristiga skulder |
| Shareholders' Equity | Eget kapital |
| Interest Expense | Räntekostnader |

### Where to Find in Swedish Reports

- Debt details: "Noter" (Notes) section
- Often labeled "Finansiella skulder" (Financial liabilities)
- Lease liabilities shown separately under IFRS 16

---

## Quick Reference

| Metric | Formula | Conservative | Concerning |
|--------|---------|--------------|------------|
| **D/E** | Debt / Equity | < 0.5 | > 2.0 |
| **Debt/EBITDA** | Debt / EBITDA | < 2x | > 4x |
| **Net Debt/EBITDA** | (Debt - Cash) / EBITDA | < 2x | > 3x |
| **Interest Coverage** | EBIT / Interest | > 5x | < 2x |
| **Debt/Assets** | Debt / Assets | < 30% | > 50% |

---

## Analysis Checklist

- [ ] What is total debt (short + long term)?
- [ ] What is net debt (debt - cash)?
- [ ] What's the Debt/EBITDA ratio?
- [ ] Can they cover interest easily (coverage > 5x)?
- [ ] When does debt mature (concentration risk)?
- [ ] Are they close to any covenants?
- [ ] Include lease liabilities for full picture?

---

## See Also

- [Balance Sheet](../financial-statements/balance-sheet.md)
- [Liquidity Metrics](liquidity.md) - Short-term solvency
- [Cash Flow Metrics](cash-flow.md) - Ability to service debt
