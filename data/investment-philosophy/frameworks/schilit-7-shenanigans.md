# Schilit's 7 Shenanigans

## Quick Reference

- **Creator**: Dr. Howard Schilit (1993, updated 2018)
- **Purpose**: Framework for detecting accounting manipulation and fraud
- **Book**: "Financial Shenanigans: How to Detect Accounting Gimmicks & Fraud"

---

## Overview

Dr. Howard Schilit, founder of Schilit Forensics (formerly CFRA), developed a systematic framework for identifying when companies manipulate their financial statements. Described as "the Sherlock Holmes of Accounting" by BusinessWeek, Schilit has testified before Congress and the SEC on accounting fraud.

The 7 Shenanigans framework categorizes the most common ways companies deceive investors. Understanding these techniques is essential for protecting capital and identifying potential short opportunities.

---

## The 7 Shenanigans

### 1. Recording Revenue Too Soon or of Questionable Quality

**What it looks like:**
- Revenue recognized before delivery of goods/services
- Bill-and-hold arrangements
- Channel stuffing (shipping excess inventory to distributors)
- Revenue from barter transactions
- Long-term contracts with aggressive assumptions

**Red flags to watch:**
- Accounts receivable growing faster than revenue
- Days Sales Outstanding (DSO) increasing
- Unusual spikes in revenue near quarter-end
- Revenue from related parties

**Questions to ask:**
- When does title pass to the customer?
- Are there unusual return policies?
- Are there contingencies attached to the sale?

---

### 2. Recording Bogus Revenue

**What it looks like:**
- Fabricated transactions
- Revenue from non-customers (subsidiaries, partners)
- Recording loans as revenue
- Grossing up net revenue arrangements

**Red flags to watch:**
- Revenue without corresponding cash flow
- Large "other revenue" or "miscellaneous" categories
- Unusual related party transactions
- Round number revenue figures

**Questions to ask:**
- Is there a legitimate customer?
- Did cash actually change hands?
- Is the revenue sustainable?

---

### 3. Boosting Income with One-Time Gains

**What it looks like:**
- Selling assets to generate gains
- Releasing reserves to income
- Investment gains masquerading as operating income
- Pension income included in operating results

**Red flags to watch:**
- Non-recurring items in "operating" income
- Asset sales coinciding with earnings misses
- Unusual gains from investments
- Reserve releases without explanation

**Questions to ask:**
- Is this repeatable?
- Why was this classified as operating income?
- What is the underlying business performance?

---

### 4. Shifting Current Expenses to a Later Period

**What it looks like:**
- Capitalizing operating expenses
- Extending depreciation/amortization periods
- Not writing down impaired assets
- Improper inventory costing

**Red flags to watch:**
- Capitalized costs growing faster than revenue
- Asset impairments always "surprising" management
- Depreciation as % of assets declining
- Inventory growing faster than sales

**Questions to ask:**
- Are capitalization policies consistent with peers?
- When was the last impairment review?
- Is depreciation period realistic?

---

### 5. Failing to Record or Improperly Reducing Liabilities

**What it looks like:**
- Understating contingent liabilities
- Not recording employee obligations
- Inadequate warranty reserves
- Off-balance sheet debt

**Red flags to watch:**
- Litigation disclosed but not reserved
- Pension underfunding
- Warranty expense declining as sales grow
- Operating leases with large future obligations

**Questions to ask:**
- Are reserves adequate for known risks?
- What's off-balance sheet?
- How do reserves compare to peers?

---

### 6. Shifting Current Revenue to a Later Period

**What it looks like:**
- Building "cookie jar" reserves in good times
- Excessive deferred revenue
- Overstating allowances

**Red flags to watch:**
- Large unusual charges followed by "recovery"
- Deferred revenue swings
- Allowance for doubtful accounts changes

**Why it matters:**
- While this seems "conservative," it allows management to smooth earnings
- Creates artificial earnings in future periods
- Indicates management prioritizes earnings targets over accuracy

---

### 7. Shifting Future Expenses to Current Period (Big Bath)

**What it looks like:**
- Kitchen-sink restructuring charges
- Excessive reserves for future costs
- Writing off good assets
- Accelerating depreciation

**Red flags to watch:**
- Massive one-time charges when new CEO arrives
- Restructuring charges every few years
- Write-offs that are later reversed

**Why it matters:**
- Sets up easy comparisons for future periods
- Hides poor current performance
- Creates "earnings beats" from reserve releases

---

## Key Warning Signs Checklist

### Accounts Receivable
- [ ] AR growing faster than revenue (DSO increasing)
- [ ] Large allowance for doubtful accounts changes
- [ ] Unusual related party receivables
- [ ] Receivables sold/factored (check footnotes)

### Revenue Quality
- [ ] Revenue growth without cash flow growth
- [ ] Unusual revenue recognition policies
- [ ] Large percentage of revenue near quarter-end
- [ ] Revenue from unusual sources

### Expenses & Capitalization
- [ ] Capitalized costs as % of revenue increasing
- [ ] Depreciation period extensions
- [ ] R&D or advertising suddenly capitalized
- [ ] Declining SG&A as % of revenue (cost-cutting hiding problems)

### Cash Flow
- [ ] Operating cash flow << Net income (accruals issue)
- [ ] Negative free cash flow with positive earnings
- [ ] Unusual cash flow statement reclassifications
- [ ] Accounts payable swings (paying suppliers slowly)

### Balance Sheet
- [ ] Off-balance sheet arrangements in footnotes
- [ ] Related party transactions
- [ ] Goodwill/intangibles as large % of assets
- [ ] Unusual liabilities categories

### Management Behavior
- [ ] Frequent accounting policy changes
- [ ] CFO departure
- [ ] Auditor change
- [ ] Delayed filings
- [ ] Heavy insider selling

---

## Implementation in Our System

### Prompt Enhancement

Add to `src/podstock/filings/analysis/deep_analysis.py`:

```python
SHENANIGANS_DETECTION_PROMPT = """Analyze this filing for potential accounting manipulation.

Check for the 7 Shenanigans:

1. REVENUE TOO SOON: Are receivables growing faster than revenue? Any channel stuffing signs?
2. BOGUS REVENUE: Any related party transactions affecting revenue? Non-cash revenue?
3. ONE-TIME GAINS: Are non-recurring items in operating income? Asset sales?
4. DEFERRED EXPENSES: Are costs being capitalized that should be expensed?
5. HIDDEN LIABILITIES: Off-balance sheet items? Underreserved contingencies?
6. DEFERRED REVENUE: Cookie jar reserves? Artificial smoothing?
7. BIG BATH: Excessive restructuring charges? Kitchen sink write-offs?

For each potential issue found:
- Describe the concern
- Rate severity: high | medium | low
- Cite the specific line item or disclosure

Return as JSON:
{
  "shenanigans_found": [
    {
      "type": "revenue_too_soon",
      "description": "DSO increased from 45 to 62 days",
      "severity": "medium",
      "evidence": "AR grew 28% while revenue grew only 12%"
    }
  ],
  "overall_risk": "low | medium | high",
  "recommendation": "..."
}
"""
```

---

## Case Studies

### Enron (2001)
- **Shenanigans**: #2 (bogus revenue), #5 (hidden liabilities)
- **Mechanism**: Mark-to-market accounting on future contracts, off-balance sheet SPEs
- **Detection**: Related party transactions in footnotes, CFO == Net Income divergence

### WorldCom (2002)
- **Shenanigans**: #4 (deferred expenses)
- **Mechanism**: Capitalized $3.8B in line costs that should have been expensed
- **Detection**: Capex as % of revenue abnormally high, cash flow didn't match earnings

### Wirecard (2020)
- **Shenanigans**: #2 (bogus revenue)
- **Mechanism**: Fabricated Asian revenue, €1.9B "trust account" didn't exist
- **Detection**: Revenue from third-party partners without corresponding cash

---

## Sources

- [Financial Shenanigans, 4th Edition - Amazon](https://www.amazon.com/Financial-Shenanigans-Fourth-Accounting-Gimmicks/dp/126011726X)
- [7 Red Flags - Intrinsic Info](https://intrinsicinfo.com/7-red-flags-indicate-company-manipulating-financials-financial-shenanigans)
- [Schilit Forensics](https://www.schilitforensics.com/)
- [Behind The Balance Sheet Podcast - Short Sellers](https://behindthebalancesheet.com/podcasts-singles/podcast-episode-15/)
