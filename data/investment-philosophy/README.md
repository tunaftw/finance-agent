# Investment Philosophy Knowledge Library

A curated collection of frameworks, techniques, and insights from the world's best investors and financial analysts. Built to support world-class analysis of company filings (10-K, 10-Q, annual reports).

## Quick Navigation

### Core Frameworks

| Framework | Purpose | Alpha Evidence |
|-----------|---------|----------------|
| [Piotroski F-Score](frameworks/piotroski-f-score.md) | 9-point financial health scoring | +7.5% annually |
| [Schilit 7 Shenanigans](frameworks/schilit-7-shenanigans.md) | Fraud & manipulation detection | Fraud prevention |
| [Buffett 10-K Method](frameworks/buffett-10k-method.md) | Qualitative filing analysis | Legendary returns |
| [Sloan Accruals](frameworks/sloan-accruals.md) | Earnings quality assessment | +10.4% CAGR |
| [Graham-Dodd Intrinsic Value](frameworks/graham-dodd-intrinsic-value.md) | Margin of safety valuation | Value investing foundation |
| [Greenblatt Magic Formula](frameworks/greenblatt-magic-formula.md) | ROIC + earnings yield | +30.8% CAGR (backtest) |

### Expert Profiles

| Expert | Known For | Primary Contribution |
|--------|-----------|---------------------|
| [Warren Buffett](experts/warren-buffett.md) | Value investing, Berkshire | Qualitative moat analysis |
| [Charlie Munger](experts/charlie-munger.md) | Mental models | Inversion, multidisciplinary thinking |
| [Howard Schilit](experts/howard-schilit.md) | Forensic accounting | 7 Shenanigans framework |
| [Jim Chanos](experts/jim-chanos.md) | Short selling | Fraud detection via filings |
| [Seth Klarman](experts/seth-klarman.md) | Baupost Group | Margin of safety |
| [Aswath Damodaran](experts/aswath-damodaran.md) | NYU Stern | Valuation education |
| [Joel Greenblatt](experts/joel-greenblatt.md) | Gotham Capital | Magic Formula, special situations |

### Techniques

| Technique | Application |
|-----------|-------------|
| [Red Flags Checklist](techniques/red-flags-checklist.md) | Comprehensive warning signs |
| [CEO Letter Analysis](techniques/ceo-letter-analysis.md) | Management communication decoding |
| [MD&A Detective Work](techniques/mda-detective-work.md) | Management Discussion analysis |
| [Footnote Mining](techniques/footnote-mining.md) | Hidden disclosure discovery |
| [Cash Flow vs Earnings](techniques/cash-flow-vs-earnings.md) | Earnings quality verification |
| [Segment Analysis](techniques/segment-analysis.md) | Business unit evaluation |
| [Related Party Transactions](techniques/related-party-transactions.md) | Governance red flags |

### Book Summaries

| Book | Author | Key Takeaway |
|------|--------|--------------|
| [Financial Shenanigans](books/financial-shenanigans.md) | Howard Schilit | 7 ways companies manipulate financials |
| [The Intelligent Investor](books/intelligent-investor.md) | Benjamin Graham | Margin of safety, Mr. Market |
| [Security Analysis](books/security-analysis.md) | Graham & Dodd | The bible of fundamental analysis |
| [Margin of Safety](books/margin-of-safety.md) | Seth Klarman | Risk-averse value investing |
| [Quality of Earnings](books/quality-of-earnings.md) | Thornton O'Glove | Earnings manipulation detection |

### Academic Research

| Paper | Author(s) | Finding |
|-------|-----------|---------|
| [Piotroski 2000](academic/piotroski-2000.md) | Joseph Piotroski | F-Score adds +7.5% alpha to value stocks |
| [Sloan 1996](academic/sloan-1996.md) | Richard Sloan | Accruals predict future returns |
| [Research Summary](academic/research-summary.md) | Various | Consolidated academic findings |

### Tools & Technology

| Tool | Use Case |
|------|----------|
| [SEC EDGAR API](tools/sec-edgar-api.md) | Programmatic US filing access |
| [XBRL Parsing](tools/xbrl-parsing.md) | Structured financial data extraction |
| [NLP Sentiment](tools/nlp-sentiment.md) | Text analysis for filings |
| [Platform Comparison](tools/platform-comparison.md) | Koyfin vs AlphaSense vs Bloomberg |

---

## How to Use This Library

### For Filing Analysis

1. **Before analyzing a filing**: Review the [Buffett 10-K Method](frameworks/buffett-10k-method.md) for the qualitative approach
2. **During analysis**: Use the [Red Flags Checklist](techniques/red-flags-checklist.md) to catch warning signs
3. **After reading**: Calculate [Piotroski F-Score](frameworks/piotroski-f-score.md) for quantitative validation
4. **Cross-reference**: Compare findings with podcast/Twitter mentions in the broader system

### For Learning

1. Start with [The Intelligent Investor](books/intelligent-investor.md) summary
2. Move to [Financial Shenanigans](books/financial-shenanigans.md) for red flags
3. Deep dive into expert profiles based on interest
4. Apply frameworks to real filings in your watchlist

### Integration with Analysis System

This library is designed to work with:
- `src/podstock/filings/analysis/deep_analysis.py` - Prompt templates reference these frameworks
- `.claude/skills/analyze-filings/SKILL.md` - Skill uses techniques from this library
- `data/filings/analysis/` - Output files incorporate framework insights

---

## Key Principles

### The Buffett-Munger Philosophy

> "Price is what you pay. Value is what you get."

1. **Understand the business first** - Read Item 1 before the financials
2. **Look for what could kill it** - Risk factors tell the truth
3. **Cash flow is truth** - Compare to reported earnings
4. **Invert, always invert** - What could go wrong?

### The Forensic Accounting Mindset

> "Figures don't lie, but liars figure." - Mark Twain

1. **Skepticism is a feature** - Question management's narrative
2. **Follow the cash** - Accruals hide reality
3. **Compare over time** - Trends reveal manipulation
4. **Check the footnotes** - Buried disclosures matter

### The Quantitative Edge

> "In God we trust; all others must bring data."

1. **F-Score works** - 9 signals with academic validation
2. **Accruals predict** - High accruals = future underperformance
3. **Combine qual + quant** - Neither alone is sufficient
4. **Systematic beats emotional** - Checklists > intuition

---

## Sources & Further Reading

### Online Resources
- [Aswath Damodaran's Free Courses](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/onlineclass.htm)
- [Buffett's Shareholder Letters](https://www.berkshirehathaway.com/letters/letters.html)
- [SEC EDGAR](https://www.sec.gov/search-filings)
- [Alpha Architect Research](https://alphaarchitect.com/)

### Podcasts
- Behind The Balance Sheet
- Invest Like the Best
- Value After Hours

---

*Last updated: 2025-12-30*
