# Buffett's 10-K Reading Method

## Quick Reference

- **Creator**: Warren Buffett, Berkshire Hathaway
- **Purpose**: Qualitative framework for understanding businesses through SEC filings
- **Key Quote**: "Read 500 pages like this every day. That's how knowledge builds up, like compound interest."

---

## Overview

Warren Buffett is famous for spending 5-6 hours a day reading annual reports and 10-K filings. His approach is fundamentally different from quantitative screens - he seeks to understand the business as if he were buying the entire company.

When asked what he and Charlie Munger look for in annual reports, Buffett explained: "We start by looking at the reports of companies that we think we can understand... and then we see from that report whether the management is telling us about the things that we would want to know about if we owned 100% of the company."

---

## The Buffett Reading Order

### Step 1: Business Description (Item 1)

**Read first, always.**

> "Understand the business before the financials."

**What to look for:**
- Can you explain what the company does in one paragraph?
- What are the key drivers of revenue?
- Who are the customers and why do they buy?
- What is the competitive landscape?
- How does the company make money?

**Red flags:**
- Overly complex business models
- Multiple unrelated segments
- Heavy reliance on acquisitions
- Buzzword-heavy descriptions

---

### Step 2: Risk Factors (Item 1A)

**Companies must legally disclose what could go wrong.**

> "Read risk factors not because you're pessimistic, but because you want to know what could kill the business."

**What to look for:**
- Competitive threats
- Regulatory risks
- Customer concentration
- Technology disruption
- Supply chain dependencies

**Technique**: Compare risk factors year-over-year
- New risks added = management sees new threats
- Risks removed = resolved or being hidden
- Language escalation = increasing concern

---

### Step 3: MD&A (Item 7)

**Management Discussion & Analysis - where management tells their story.**

> "Read MD&A like a detective reads a witness statement. Look for consistency, credibility, and candor."

**What to look for:**
- How does management explain results?
- Are they realistic or spinning?
- What challenges do they acknowledge?
- What are they NOT saying?
- How do they explain misses?

**Questions to ask:**
- Is management honest about problems?
- Do explanations match the numbers?
- Are promises from last year addressed?
- What's the tone - confident or defensive?

---

### Step 4: Cash Flow Statement

**The truth serum of financial statements.**

> "The cash flow statement is where the truth lives. WorldCom reported tremendous income growth, but if you looked at cash flow net of investing, they were actually hemorrhaging cash."

**What to look for:**
- Is operating cash flow > net income? (quality earnings)
- Is free cash flow consistently positive?
- How much capex is needed to maintain the business?
- Are there unusual working capital swings?

**Buffett's "Owner Earnings" Formula:**
```
Owner Earnings = Net Income
                 + Depreciation/Amortization
                 - Maintenance CapEx
                 - Required Working Capital Increases
```

---

### Step 5: Footnotes

**Where the bodies are buried.**

> "The footnotes often contain the most important information."

**Critical footnotes:**
- Revenue recognition policies
- Off-balance sheet arrangements
- Related party transactions
- Contingent liabilities
- Lease obligations
- Pension assumptions
- Stock compensation

**Red flags in footnotes:**
- Complex structures with no clear purpose
- Related party transactions
- Aggressive assumptions
- Unusual accounting treatments
- Frequent policy changes

---

## Key Financial Metrics (Buffett Style)

### Return on Equity (ROE)

> "We like companies that earn high returns on equity while utilizing little debt."

**Target**: Consistent ROE > 15% over 10+ years

**Calculation**:
```
ROE = Net Income / Shareholders' Equity
```

**Caveat**: High debt inflates ROE - use ROIC for more accuracy

---

### Profit Margins

> "Durable competitive advantage shows up in profit margins."

**What Buffett looks for:**
- Gross margin > 40% (often indicates pricing power)
- Operating margin stability over time
- Net margin > 20% for exceptional businesses

---

### Capital Expenditure Ratio

> "A company with durable competitive advantage uses a smaller portion of earnings for capital expenditure."

**Calculation**:
```
CapEx Ratio = Capital Expenditure / Net Income
```

**Interpretation**:
- < 25% = likely has competitive advantage
- 25-50% = good place to look
- > 50% = capital intensive, may lack moat

---

### Debt to Equity

> "We like companies that can pay off all their debt in 3-4 years from earnings."

**Quick test**:
```
Debt Payoff Years = Total Debt / Net Income
```

**Interpretation**:
- < 4 years = comfortable
- 4-7 years = moderate concern
- > 7 years = high leverage

---

## The Moat Checklist

Buffett's "economic moat" indicators:

### Qualitative Signs
- [ ] Brand recognition (pricing power)
- [ ] Patents or proprietary technology
- [ ] High switching costs for customers
- [ ] Network effects
- [ ] Cost advantages (scale, location)
- [ ] Regulatory barriers to entry

### Quantitative Signs
- [ ] High and stable ROE over 10+ years
- [ ] Growing earnings with stable margins
- [ ] Low capital requirements
- [ ] Strong free cash flow
- [ ] Minimal debt
- [ ] Consistent dividend/buyback history

---

## Reading for Candor

### Signs of Honest Management

> "We want managers who, whether the news is good or bad, give us a complete report."

**Positive signals:**
- Acknowledges failures and mistakes
- Explains what went wrong, not just what went right
- Provides specific, measurable goals
- Addresses previous year's promises
- Gives honest competitive assessment

### Signs of Spin

**Warning signals:**
- Only discusses positives
- Blames external factors for all problems
- Vague, unmeasurable goals
- Ignores previous guidance misses
- Excessive use of adjusted/non-GAAP metrics
- Complex explanations for simple questions

---

## Implementation in Our System

### CEO Letter Analysis Enhancement

Add to `src/podstock/filings/analysis/ceo_letter.py`:

```python
BUFFETT_CANDOR_PROMPT = """Analyze the CEO letter for candor and honesty.

Rate the following (1-5 scale):

1. HONESTY ABOUT PROBLEMS
   - Does management acknowledge failures?
   - Are explanations realistic or blame-shifting?

2. SPECIFICITY
   - Are goals measurable and trackable?
   - Are prior year promises addressed?

3. COMPETITIVE REALITY
   - Does management acknowledge competition?
   - Is the market assessment realistic?

4. OWNER ORIENTATION
   - Does management think like owners?
   - Is capital allocation discussed honestly?

5. CONSISTENCY
   - Does the narrative match the numbers?
   - Is the tone appropriate to results?

Return:
{
  "candor_score": 1-5,
  "owner_orientation": 1-5,
  "red_flags": ["..."],
  "positive_signals": ["..."],
  "key_quotes": ["..."]
}
"""
```

### MD&A Detective Prompt

```python
MDA_DETECTIVE_PROMPT = """Read this MD&A like a detective.

Look for:
1. CONSISTENCY
   - Do explanations match the numbers?
   - Are there contradictions?

2. CREDIBILITY
   - Are claims verifiable?
   - Is the tone appropriate?

3. CANDOR
   - What are they NOT saying?
   - What problems are glossed over?

4. YEAR-OVER-YEAR
   - What changed in the narrative?
   - Were last year's promises kept?

Return analysis with evidence from the text.
"""
```

---

## Key Quotes from Buffett

> "Price is what you pay. Value is what you get."

> "It's far better to buy a wonderful company at a fair price than a fair company at a wonderful price."

> "When a management with a reputation for brilliance tackles a business with a reputation for bad economics, it is the reputation of the business that remains intact."

> "You should invest in a business that even a fool can run, because someday a fool will."

> "Risk comes from not knowing what you're doing."

---

## Sources

- [How to Read a 10-K Like Warren Buffett - CNBC](https://www.cnbc.com/2014/01/27/how-to-read-a-10-k-like-warren-buffet.html)
- [Jimmy's Journal - 10-K Analysis](https://jimmysjournal.substack.com/p/how-to-read-a-10-k-like-warren-buffett)
- [GuruFocus - Buffett's Annual Report Reading](https://www.gurufocus.com/news/2088446/invest-like-a-pro-by-reading-annual-reports-the-warren-buffett-way)
- [Old School Value - Buffett Financial Statements](https://www.oldschoolvalue.com/tutorial/this-is-how-buffett-interprets-financial-statements/)
- [The Rational Walk - 10-K Reading Guide](https://rationalwalk.com/how-to-read-a-10-k-annual-report-efficiently/)
- [Berkshire Hathaway Shareholder Letters](https://www.berkshirehathaway.com/letters/letters.html)
