# Howard Schilit

## Profile

- **Full Name**: Howard Mark Schilit, PhD, CPA
- **Known For**: Forensic accounting, fraud detection, "Financial Shenanigans" book
- **Organization**: Schilit Forensics (founder); formerly CFRA (founded 1994)
- **Key Works**: *Financial Shenanigans* (1993, 2002, 2010, 2018)

---

## Background

Dr. Howard Schilit is a pioneer in forensic accounting and the detection of accounting manipulation. Described as "the Sherlock Holmes of Accounting" by BusinessWeek, he has:

- Testified before Congress and the SEC on accounting fraud
- Founded CFRA (Center for Financial Research and Analysis) in 1994
- Advised institutional investors on earnings quality
- Published research identifying frauds before they were publicly known

His book *Financial Shenanigans* has become the definitive guide for detecting accounting manipulation, now in its 4th edition (2018) with co-authors Jeremy Perler and Yoni Engelhart.

---

## Investment Philosophy

### Core Belief

> "Figures don't lie, but liars figure." - Mark Twain

Schilit's approach is fundamentally skeptical. He assumes management has incentives to present results in the best possible light and that investors must actively search for manipulation.

### The Forensic Mindset

1. **Question everything** - Don't take financial statements at face value
2. **Follow the cash** - Accrual accounting creates manipulation opportunities
3. **Compare over time** - Trends reveal what single periods hide
4. **Read the footnotes** - Important disclosures are often buried
5. **Compare to peers** - Outliers deserve investigation

---

## The 7 Shenanigans Framework

### Overview

Schilit identified seven primary categories of financial manipulation:

| # | Shenanigan | Purpose |
|---|------------|---------|
| 1 | Recording revenue too soon | Inflate current revenue |
| 2 | Recording bogus revenue | Create fake revenue |
| 3 | Boosting income with one-time gains | Hide operating weakness |
| 4 | Shifting current expenses to later | Inflate current earnings |
| 5 | Reducing/failing to record liabilities | Understate obligations |
| 6 | Shifting current revenue to later | Create cookie jars |
| 7 | Shifting future expenses to current | Enable future beats |

See [Schilit 7 Shenanigans Framework](../frameworks/schilit-7-shenanigans.md) for detailed analysis.

---

## Filing Analysis Approach

### Key Warning Signs

**Revenue Quality:**
- Accounts receivable growing faster than revenue
- Days Sales Outstanding (DSO) increasing
- Revenue from related parties
- Unusual recognition policies

**Expense Management:**
- Capitalizing what should be expensed
- Extending depreciation periods
- Delaying write-offs

**Cash Flow:**
- Net income >> Operating cash flow (persistent)
- Negative free cash flow with positive earnings
- Unusual working capital changes

**Management Behavior:**
- Frequent accounting policy changes
- CFO departures
- Auditor changes
- Excessive non-GAAP adjustments

### The Receivables Test

One of Schilit's most reliable indicators:

```
If: AR Growth > Revenue Growth
Then: Investigate immediately

Potential causes:
- Channel stuffing
- Aggressive revenue recognition
- Collection problems
- Customer concentration issues
```

---

## Key Quotes

### On Skepticism

> "Investors must develop a healthy skepticism when reading financial reports."

### On Cash Flow

> "Cash flow from operations is much harder to manipulate than earnings."

### On Footnotes

> "The most important information is often buried in the footnotes."

### On the Current Environment

> "We are in the golden age of fraud." - Jim Chanos (echoing Schilit's concerns)

---

## Famous Fraud Detection Cases

### Enron (2001)
- **Detected**: Off-balance sheet entities, related party transactions
- **Key signals**: Complex structures in footnotes, CFO conflicts

### WorldCom (2002)
- **Detected**: Capitalizing line costs as assets
- **Key signals**: Capex/revenue ratio abnormally high

### Tyco (2002)
- **Detected**: Acquisition accounting manipulation
- **Key signals**: Serial acquisitions, pro forma adjustments

### HealthSouth (2003)
- **Detected**: Fabricated revenue
- **Key signals**: Per-share earnings always meeting estimates exactly

---

## What We Can Learn

### For Filing Analysis

1. **Calculate DSO every quarter** - Track accounts receivable vs revenue trend

2. **Compare OCF to Net Income** - Persistent gaps are red flags

3. **Read footnotes carefully** - Especially:
   - Revenue recognition policies
   - Related party transactions
   - Off-balance sheet arrangements
   - Contingent liabilities

4. **Watch for policy changes** - Ask "why now?"

5. **Compare to peers** - Outlier metrics deserve investigation

### Checklist Questions

Ask these for every filing:

- [ ] Is revenue growth supported by cash collection?
- [ ] Are expenses being properly matched to revenue?
- [ ] What's off the balance sheet?
- [ ] How does management talk about problems?
- [ ] What changed since last filing?

---

## Books

| Title | Edition | Year | Notes |
|-------|---------|------|-------|
| *Financial Shenanigans* | 4th | 2018 | Current, comprehensive |
| *Financial Shenanigans* | 3rd | 2010 | Post-financial crisis updates |
| *Financial Shenanigans* | 2nd | 2002 | Post-Enron updates |
| *Financial Shenanigans* | 1st | 1993 | Original framework |

**Recommended**: Start with 4th edition for most current examples and techniques.

---

## Related Experts

| Expert | Specialty | Connection |
|--------|-----------|------------|
| Jim Chanos | Short selling | Uses Schilit's framework for fraud detection |
| Thornton O'Glove | Quality of Earnings | Complementary approach |
| Carson Block | Muddy Waters | Modern application of forensic techniques |
| John Hempton | Bronte Capital | Short research methodology |

---

## Resources

### Schilit Forensics
- Website: [schilitforensics.com](https://www.schilitforensics.com/)
- Provides institutional research and consulting

### Academic Papers
- Papers on earnings manipulation detection
- Research on accruals and earnings quality

---

## Implementation

### Prompt for Forensic Analysis

```python
SCHILIT_FORENSIC_PROMPT = """Analyze this filing using Schilit's forensic accounting approach.

Check for all 7 Shenanigans:
1. Revenue recorded too soon or of questionable quality
2. Bogus revenue
3. One-time gains boosting income
4. Current expenses shifted to later periods
5. Liabilities understated or unrecorded
6. Current revenue shifted to later (cookie jars)
7. Future expenses shifted to current (big bath)

For each concern:
- Identify the specific issue
- Cite evidence from the filing
- Rate severity: high | medium | low
- Note if this is new or ongoing

Also check:
- DSO trend (AR vs Revenue growth)
- OCF vs Net Income gap
- Related party transactions
- Accounting policy changes

Return structured analysis with overall manipulation risk assessment.
"""
```

---

## Sources

- [Financial Shenanigans, 4th Edition - Amazon](https://www.amazon.com/Financial-Shenanigans-Fourth-Accounting-Gimmicks/dp/126011726X)
- [Intrinsic Info - 7 Red Flags](https://intrinsicinfo.com/7-red-flags-indicate-company-manipulating-financials-financial-shenanigans)
- [Behind The Balance Sheet Podcast](https://behindthebalancesheet.com/podcasts-singles/podcast-episode-15/)
- BusinessWeek profiles and interviews
