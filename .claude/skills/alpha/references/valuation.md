# Valuation Module

Quantitative backbone for fair value calculation. Used after agents gather qualitative data to produce the final valuation with Bull/Base/Bear scenarios.

---

## Bolagsklassificering

Map company types to relevant valuation multiples. Always include FCF yield and Nettoskuld/EBITDA for all types.

| Bolagstyp | Primara multiplar | Sekundara multiplar | Kommentar |
|-----------|-------------------|---------------------|-----------|
| Bank/Finans | P/B, P/E | ROE, CET1-ratio | Bokfort eget kapital ar nyckeln |
| Gaming/Betting | EV/EBITDA, P/E | FCF yield, Revenue growth | Hog kassa, laga capex |
| SaaS/Tech | EV/Sales, Rule of 40 | ARR growth, NRR, CAC/LTV | Tillvaxt viktigare an vinst |
| Industri/Cyklisk | EV/EBITDA, ROIC | P/E (mid-cycle), kapitalintensitet | Normalisera for cykel |
| Fastighet | P/NAV, FFO yield | LTV, substansvarde | Rabatt/premie mot NAV |
| Konsument | P/E, EV/EBIT | Omsattningstillvaxt, marginaltrend | Stabilitet premiumvarderas |

**Alltid inkludera:**
- FCF yield (Free Cash Flow / Market Cap)
- Nettoskuld/EBITDA

---

## Python Functions

### calculate_multiples()

Calculate standard valuation multiples from financial data.

```python
def calculate_multiples(
    financials: dict,
    market_cap: float,
    net_debt: float
) -> dict:
    """
    Calculate valuation multiples from financial data.

    Args:
        financials: Dict with keys:
            - revenue: Annual revenue
            - ebitda: EBITDA
            - ebit: EBIT (operating income)
            - net_income: Net income
            - fcf: Free cash flow
            - shares_outstanding: Number of shares
        market_cap: Market capitalization
        net_debt: Net debt (positive = debt, negative = net cash)

    Returns:
        Dict with calculated multiples:
            - pe: Price/Earnings
            - ev_ebitda: EV/EBITDA
            - ev_sales: EV/Sales
            - p_fcf: Price/FCF
            - fcf_yield: FCF Yield (%)
            - net_debt_ebitda: Net Debt/EBITDA

    Example:
        >>> financials = {
        ...     'revenue': 10000,
        ...     'ebitda': 2000,
        ...     'ebit': 1500,
        ...     'net_income': 1000,
        ...     'fcf': 800,
        ...     'shares_outstanding': 100
        ... }
        >>> calculate_multiples(financials, market_cap=15000, net_debt=3000)
        {
            'pe': 15.0,
            'ev_ebitda': 9.0,
            'ev_sales': 1.8,
            'p_fcf': 18.75,
            'fcf_yield': 5.33,
            'net_debt_ebitda': 1.5
        }
    """
    ev = market_cap + net_debt

    result = {}

    # P/E - handle negative earnings
    if financials.get('net_income') and financials['net_income'] > 0:
        result['pe'] = round(market_cap / financials['net_income'], 2)
    else:
        result['pe'] = None

    # EV/EBITDA
    if financials.get('ebitda') and financials['ebitda'] > 0:
        result['ev_ebitda'] = round(ev / financials['ebitda'], 2)
    else:
        result['ev_ebitda'] = None

    # EV/Sales
    if financials.get('revenue') and financials['revenue'] > 0:
        result['ev_sales'] = round(ev / financials['revenue'], 2)
    else:
        result['ev_sales'] = None

    # P/FCF
    if financials.get('fcf') and financials['fcf'] > 0:
        result['p_fcf'] = round(market_cap / financials['fcf'], 2)
    else:
        result['p_fcf'] = None

    # FCF Yield (%)
    if financials.get('fcf') and market_cap > 0:
        result['fcf_yield'] = round((financials['fcf'] / market_cap) * 100, 2)
    else:
        result['fcf_yield'] = None

    # Net Debt/EBITDA
    if financials.get('ebitda') and financials['ebitda'] > 0:
        result['net_debt_ebitda'] = round(net_debt / financials['ebitda'], 2)
    else:
        result['net_debt_ebitda'] = None

    return result
```

---

### build_scenarios()

Build Bull/Base/Bear valuation scenarios.

```python
def build_scenarios(
    base_ebitda: float,
    base_multiple: float,
    net_debt: float,
    shares: float,
    bull_ebitda_adj: float = 0.20,
    bull_multiple_adj: float = 1.0,
    bear_ebitda_adj: float = -0.20,
    bear_multiple_adj: float = -1.5
) -> list[dict]:
    """
    Build Bull/Base/Bear valuation scenarios.

    Args:
        base_ebitda: Base case EBITDA
        base_multiple: Base case EV/EBITDA multiple
        net_debt: Net debt (positive = debt, negative = net cash)
        shares: Shares outstanding
        bull_ebitda_adj: Bull case EBITDA adjustment (default: +20%)
        bull_multiple_adj: Bull case multiple adjustment (default: +1.0x)
        bear_ebitda_adj: Bear case EBITDA adjustment (default: -20%)
        bear_multiple_adj: Bear case multiple adjustment (default: -1.5x)

    Returns:
        List of scenario dicts, each containing:
            - name: Scenario name (Bull/Base/Bear)
            - probability: Default probability weight
            - ebitda: Scenario EBITDA
            - multiple: Scenario multiple
            - ev: Enterprise Value
            - equity_value: Equity Value (EV - net_debt)
            - fair_value: Fair value per share

    Example:
        >>> scenarios = build_scenarios(
        ...     base_ebitda=2000,
        ...     base_multiple=10.0,
        ...     net_debt=3000,
        ...     shares=100
        ... )
        >>> # Bull: EBITDA=2400, Multiple=11.0x, EV=26400, FV=234.0
        >>> # Base: EBITDA=2000, Multiple=10.0x, EV=20000, FV=170.0
        >>> # Bear: EBITDA=1600, Multiple=8.5x, EV=13600, FV=106.0
    """
    scenarios = []

    # Bull case
    bull_ebitda = base_ebitda * (1 + bull_ebitda_adj)
    bull_multiple = base_multiple + bull_multiple_adj
    bull_ev = bull_ebitda * bull_multiple
    bull_equity = bull_ev - net_debt
    bull_fv = bull_equity / shares

    scenarios.append({
        'name': 'Bull',
        'probability': 0.25,
        'ebitda': round(bull_ebitda, 0),
        'multiple': round(bull_multiple, 1),
        'ev': round(bull_ev, 0),
        'equity_value': round(bull_equity, 0),
        'fair_value': round(bull_fv, 2)
    })

    # Base case
    base_ev = base_ebitda * base_multiple
    base_equity = base_ev - net_debt
    base_fv = base_equity / shares

    scenarios.append({
        'name': 'Base',
        'probability': 0.50,
        'ebitda': round(base_ebitda, 0),
        'multiple': round(base_multiple, 1),
        'ev': round(base_ev, 0),
        'equity_value': round(base_equity, 0),
        'fair_value': round(base_fv, 2)
    })

    # Bear case
    bear_ebitda = base_ebitda * (1 + bear_ebitda_adj)
    bear_multiple = base_multiple + bear_multiple_adj
    bear_ev = bear_ebitda * bear_multiple
    bear_equity = bear_ev - net_debt
    bear_fv = bear_equity / shares

    scenarios.append({
        'name': 'Bear',
        'probability': 0.25,
        'ebitda': round(bear_ebitda, 0),
        'multiple': round(bear_multiple, 1),
        'ev': round(bear_ev, 0),
        'equity_value': round(bear_equity, 0),
        'fair_value': round(bear_fv, 2)
    })

    return scenarios
```

---

### calculate_fair_value()

Calculate probability-weighted fair value from scenarios.

```python
def calculate_fair_value(
    scenarios: list[dict],
    shares_outstanding: float = None
) -> dict:
    """
    Calculate weighted fair value from probability-weighted scenarios.

    Args:
        scenarios: List of scenario dicts from build_scenarios()
            Each must have 'probability' and 'fair_value' keys
        shares_outstanding: Optional, for validation only

    Returns:
        Dict with:
            - weighted_fair_value: Probability-weighted fair value per share
            - bull_contribution: Bull case contribution to weighted value
            - base_contribution: Base case contribution to weighted value
            - bear_contribution: Bear case contribution to weighted value
            - total_probability: Sum of probabilities (should be 1.0)

    Example:
        >>> scenarios = [
        ...     {'name': 'Bull', 'probability': 0.25, 'fair_value': 234.0},
        ...     {'name': 'Base', 'probability': 0.50, 'fair_value': 170.0},
        ...     {'name': 'Bear', 'probability': 0.25, 'fair_value': 106.0}
        ... ]
        >>> calculate_fair_value(scenarios)
        {
            'weighted_fair_value': 170.0,
            'bull_contribution': 58.5,
            'base_contribution': 85.0,
            'bear_contribution': 26.5,
            'total_probability': 1.0
        }
    """
    weighted_sum = 0.0
    total_prob = 0.0
    contributions = {}

    for scenario in scenarios:
        prob = scenario['probability']
        fv = scenario['fair_value']
        contribution = prob * fv
        weighted_sum += contribution
        total_prob += prob
        contributions[scenario['name'].lower() + '_contribution'] = round(contribution, 2)

    return {
        'weighted_fair_value': round(weighted_sum, 2),
        **contributions,
        'total_probability': round(total_prob, 2)
    }
```

---

### generate_verdict()

Generate investment verdict based on valuation analysis.

```python
def generate_verdict(
    weighted_fv: float,
    current_price: float,
    confidence: str,
    scenarios: list[dict],
    key_risks: list[str]
) -> dict:
    """
    Generate investment verdict based on fair value vs current price.

    Verdict thresholds (upside/downside from current price):
        - KOPVARD: >20% upside
        - ATTRAKTIV: 5% to 20% upside
        - FAIR: -10% to 5%
        - FULLVARDERAD: -20% to -10%
        - OVERVARDERAD: <-20% (more than 20% downside)

    Args:
        weighted_fv: Weighted fair value per share
        current_price: Current stock price
        confidence: Confidence level ('high', 'medium', 'low')
        scenarios: List of scenario dicts with fair_value
        key_risks: List of key risk strings

    Returns:
        Dict with:
            - verdict: One of KOPVARD/ATTRAKTIV/FAIR/FULLVARDERAD/OVERVARDERAD
            - upside_pct: Percentage upside/downside to fair value
            - confidence: Confidence level
            - price_targets: Dict with bull/base/bear price targets
            - margin_of_safety: Discount to base case (%)
            - risk_adjusted_verdict: Verdict adjusted for risk count
            - summary: Human-readable verdict summary

    Example:
        >>> generate_verdict(
        ...     weighted_fv=170.0,
        ...     current_price=140.0,
        ...     confidence='medium',
        ...     scenarios=[
        ...         {'name': 'Bull', 'fair_value': 234.0},
        ...         {'name': 'Base', 'fair_value': 170.0},
        ...         {'name': 'Bear', 'fair_value': 106.0}
        ...     ],
        ...     key_risks=['Regulatory risk', 'Competition']
        ... )
        {
            'verdict': 'ATTRAKTIV',
            'upside_pct': 21.43,
            'confidence': 'medium',
            'price_targets': {'bull': 234.0, 'base': 170.0, 'bear': 106.0},
            'margin_of_safety': 17.65,
            'risk_adjusted_verdict': 'ATTRAKTIV',
            'summary': 'Aktien handlas 21% under viktat fair value...'
        }
    """
    # Calculate upside/downside
    upside_pct = ((weighted_fv - current_price) / current_price) * 100

    # Determine base verdict
    if upside_pct > 20:
        verdict = 'KOPVARD'
    elif upside_pct > 5:
        verdict = 'ATTRAKTIV'
    elif upside_pct >= -10:
        verdict = 'FAIR'
    elif upside_pct >= -20:
        verdict = 'FULLVARDERAD'
    else:
        verdict = 'OVERVARDERAD'

    # Extract price targets
    price_targets = {}
    base_fv = weighted_fv  # fallback
    for s in scenarios:
        name = s['name'].lower()
        price_targets[name] = s['fair_value']
        if name == 'base':
            base_fv = s['fair_value']

    # Margin of safety (discount to base case)
    margin_of_safety = ((base_fv - current_price) / base_fv) * 100 if base_fv > 0 else 0

    # Risk-adjusted verdict (downgrade if many risks)
    risk_adjusted_verdict = verdict
    if len(key_risks) >= 5 and verdict in ['KOPVARD', 'ATTRAKTIV']:
        # Downgrade by one level if many risks
        if verdict == 'KOPVARD':
            risk_adjusted_verdict = 'ATTRAKTIV'
        elif verdict == 'ATTRAKTIV':
            risk_adjusted_verdict = 'FAIR'

    # Also downgrade if low confidence
    if confidence == 'low' and risk_adjusted_verdict in ['KOPVARD', 'ATTRAKTIV']:
        if risk_adjusted_verdict == 'KOPVARD':
            risk_adjusted_verdict = 'ATTRAKTIV'
        elif risk_adjusted_verdict == 'ATTRAKTIV':
            risk_adjusted_verdict = 'FAIR'

    # Generate summary
    direction = 'under' if upside_pct > 0 else 'over'
    abs_pct = abs(round(upside_pct))

    confidence_text = {
        'high': 'med hog konfidens',
        'medium': 'med medel konfidens',
        'low': 'med lag konfidens'
    }.get(confidence, '')

    verdict_descriptions = {
        'KOPVARD': f'Aktien handlas {abs_pct}% {direction} viktat fair value {confidence_text}. Ser kopvard ut.',
        'ATTRAKTIV': f'Aktien handlas {abs_pct}% {direction} viktat fair value {confidence_text}. Attraktiv nivaer.',
        'FAIR': f'Aktien handlas nara fair value ({abs_pct}% {direction}) {confidence_text}. Varken billig eller dyr.',
        'FULLVARDERAD': f'Aktien handlas {abs_pct}% {direction} viktat fair value {confidence_text}. Begransad uppsida.',
        'OVERVARDERAD': f'Aktien handlas {abs_pct}% {direction} viktat fair value {confidence_text}. Overvarderad.'
    }

    summary = verdict_descriptions.get(risk_adjusted_verdict, '')
    if len(key_risks) > 0:
        summary += f' Notera {len(key_risks)} identifierade risker.'

    return {
        'verdict': verdict,
        'upside_pct': round(upside_pct, 2),
        'confidence': confidence,
        'price_targets': price_targets,
        'margin_of_safety': round(margin_of_safety, 2),
        'risk_adjusted_verdict': risk_adjusted_verdict,
        'summary': summary
    }
```

---

## Usage Example

Complete valuation workflow:

```python
# 1. Company financials
financials = {
    'revenue': 15000,      # MSEK
    'ebitda': 3000,        # MSEK
    'ebit': 2500,          # MSEK
    'net_income': 1800,    # MSEK
    'fcf': 1500,           # MSEK
    'shares_outstanding': 200  # million shares
}

market_cap = 30000  # MSEK
net_debt = 5000     # MSEK
current_price = 150  # SEK

# 2. Calculate current multiples
multiples = calculate_multiples(financials, market_cap, net_debt)
# {'pe': 16.67, 'ev_ebitda': 11.67, 'ev_sales': 2.33, ...}

# 3. Build scenarios (Gaming company - use EV/EBITDA)
scenarios = build_scenarios(
    base_ebitda=3000,
    base_multiple=10.0,  # Conservative for gaming
    net_debt=5000,
    shares=200
)

# 4. Calculate weighted fair value
fv_result = calculate_fair_value(scenarios)
weighted_fv = fv_result['weighted_fair_value']

# 5. Generate verdict
verdict = generate_verdict(
    weighted_fv=weighted_fv,
    current_price=current_price,
    confidence='medium',
    scenarios=scenarios,
    key_risks=['Regulatory tightening', 'Market share loss']
)

print(f"Verdict: {verdict['risk_adjusted_verdict']}")
print(f"Upside: {verdict['upside_pct']}%")
print(verdict['summary'])
```

---

## Sector-Specific Adjustments

### Gaming/Betting
- Use trailing 12-month EBITDA (less seasonal)
- Adjust for license costs in different jurisdictions
- Watch customer acquisition cost trends

### SaaS/Tech
- Focus on EV/Sales for unprofitable companies
- Rule of 40 = Revenue growth % + EBIT margin %
- ARR more relevant than trailing revenue

### Banks/Finance
- P/B primary multiple (book value = capital)
- ROE must exceed cost of equity (~10%)
- Watch CET1 ratio for capital buffers

### Real Estate (Fastighet)
- P/NAV (discount/premium to net asset value)
- FFO yield = Funds From Operations / Price
- LTV = Loan-to-Value ratio

### Cyclical/Industrial
- Use mid-cycle earnings (normalize for cycle)
- ROIC > WACC for value creation
- Capex intensity affects FCF conversion
