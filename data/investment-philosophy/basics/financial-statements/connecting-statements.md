# How the Three Financial Statements Connect

## Quick Answer

The three financial statements are interconnected - changes in one affect the others. Understanding these links helps you spot inconsistencies and verify that numbers make sense.

---

## The Big Picture

```
                    ┌─────────────────────┐
                    │  INCOME STATEMENT   │
                    │  (Period: Q or Year)│
                    │                     │
                    │  Revenue            │
                    │  - Expenses         │
                    │  ─────────────      │
                    │  = Net Income ──────┼──────┐
                    └─────────────────────┘      │
                              │                   │
                              ▼                   ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                     CASH FLOW STATEMENT                      │
    │                     (Period: Q or Year)                      │
    │                                                              │
    │  Net Income ◄────────────────────────────────────────────────┤
    │  + Depreciation (from Income Statement)                     │
    │  ± Working Capital Changes (from Balance Sheet)             │
    │  = Operating Cash Flow                                       │
    │  - CapEx                                                     │
    │  = Free Cash Flow                                            │
    │                                                              │
    │  Net Change in Cash ─────────────────────────────────────────┼──┐
    └─────────────────────────────────────────────────────────────┘  │
                                                                      │
                              ┌────────────────────────────────────┘
                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                      BALANCE SHEET                          │
    │                   (Point in time: End of period)            │
    │                                                             │
    │  Cash ◄─────────────────────────────────────────────────────┤
    │  + Other Assets                                             │
    │  ─────────────────                                          │
    │  = Total Assets                                             │
    │                                                             │
    │  Liabilities                                                │
    │  + Equity ◄───────── Net Income adds to Retained Earnings   │
    │  ─────────────────                                          │
    │  = Total Liab + Equity (= Total Assets)                     │
    └─────────────────────────────────────────────────────────────┘
```

---

## The Key Connections

### Connection 1: Net Income → Retained Earnings

**Flow**: Income Statement → Balance Sheet

```
Ending Retained Earnings = Beginning Retained Earnings
                         + Net Income
                         - Dividends Paid
```

**What it means**: Profits accumulate on the balance sheet as retained earnings.

**Verification**:
- Check that retained earnings change = net income - dividends
- If it doesn't match, look for "other comprehensive income" adjustments

---

### Connection 2: Net Income → Cash Flow Statement

**Flow**: Income Statement → Cash Flow Statement

```
Cash Flow from Operations starts with Net Income,
then adjusts for:
  + Non-cash expenses (depreciation, stock comp)
  ± Changes in working capital
```

**What it means**: Cash flow "reconciles" accrual earnings to actual cash.

**Verification**:
- Over time, cumulative OCF should roughly equal cumulative net income
- Persistent divergence = quality issue

---

### Connection 3: Cash Flow → Balance Sheet Cash

**Flow**: Cash Flow Statement → Balance Sheet

```
Ending Cash = Beginning Cash + Net Change in Cash

Where:
Net Change in Cash = Operating CF + Investing CF + Financing CF
```

**What it means**: The cash flow statement explains why cash changed.

**Verification**:
- Cash from prior balance sheet + net change = current cash
- This MUST tie exactly

---

### Connection 4: Working Capital Links

**Flow**: Balance Sheet ↔ Cash Flow Statement

Changes in working capital items flow through operating cash flow:

| Balance Sheet Change | Cash Flow Impact |
|---------------------|------------------|
| Receivables ↑ | Cash ↓ (sold but didn't collect) |
| Inventory ↑ | Cash ↓ (bought but didn't sell) |
| Payables ↑ | Cash ↑ (bought but didn't pay) |
| Prepaid ↑ | Cash ↓ (paid in advance) |
| Deferred Revenue ↑ | Cash ↑ (collected but didn't earn) |

---

### Connection 5: Depreciation Links

**Flow**: All three statements

```
Income Statement: Depreciation is an EXPENSE (reduces net income)
Cash Flow:        ADD BACK depreciation (it's non-cash)
Balance Sheet:    PP&E decreases (accumulated depreciation increases)
```

**The magic**: Depreciation reduces taxes (real cash savings) without being a cash outflow.

---

### Connection 6: CapEx Links

**Flow**: Cash Flow → Balance Sheet

```
Ending PP&E = Beginning PP&E + CapEx - Depreciation - Disposals
```

**Verification**:
- CapEx from cash flow should roughly match PP&E increase + depreciation

---

## Worked Example

### Period Start (Balance Sheet)

| Item | MSEK |
|------|------|
| Cash | 100 |
| Receivables | 200 |
| Inventory | 150 |
| PP&E (net) | 500 |
| **Total Assets** | **950** |
| Payables | 100 |
| Debt | 300 |
| **Total Liabilities** | **400** |
| Retained Earnings | 450 |
| Share Capital | 100 |
| **Total Equity** | **550** |

### During the Period (Income Statement)

| Item | MSEK |
|------|------|
| Revenue | 1,000 |
| COGS | (600) |
| SG&A | (200) |
| Depreciation | (50) |
| Interest | (20) |
| Tax | (30) |
| **Net Income** | **100** |

### Cash Flow Statement

| Item | MSEK |
|------|------|
| Net Income | 100 |
| + Depreciation | 50 |
| - Increase in Receivables | (30) |
| - Increase in Inventory | (20) |
| + Increase in Payables | 15 |
| **Operating Cash Flow** | **115** |
| - CapEx | (80) |
| **Investing Cash Flow** | **(80)** |
| - Dividends | (25) |
| **Financing Cash Flow** | **(25)** |
| **Net Change in Cash** | **10** |

### Period End (Balance Sheet)

| Item | Calculation | MSEK |
|------|-------------|------|
| Cash | 100 + 10 | **110** |
| Receivables | 200 + 30 | **230** |
| Inventory | 150 + 20 | **170** |
| PP&E | 500 + 80 - 50 | **530** |
| **Total Assets** | | **1,040** |
| Payables | 100 + 15 | **115** |
| Debt | unchanged | **300** |
| **Total Liabilities** | | **415** |
| Retained Earnings | 450 + 100 - 25 | **525** |
| Share Capital | unchanged | **100** |
| **Total Equity** | | **625** |

**Verification**: Assets (1,040) = Liab (415) + Equity (625) ✓

---

## Red Flags from Connections

### When Things Don't Add Up

| Check | Red Flag |
|-------|----------|
| Retained Earnings change ≠ NI - Dividends | Look for OCI or restatements |
| Cash change ≠ sum of cash flows | Error or unusual item |
| OCF persistently << NI | Accruals manipulation |
| PP&E increase >> CapEx | Acquisitions or revaluations |
| Working capital swings don't match | Classification games |

---

## Quick Verification Checklist

- [ ] Cash: Does beginning + net change = ending?
- [ ] Retained Earnings: Does beginning + NI - Div = ending?
- [ ] PP&E: Does beginning + CapEx - Depreciation ≈ ending?
- [ ] Working Capital: Do the changes flow through OCF correctly?
- [ ] Total: Does Assets = Liabilities + Equity?

---

## See Also

- [Income Statement](income-statement.md)
- [Balance Sheet](balance-sheet.md)
- [Cash Flow Statement](cash-flow-statement.md)
