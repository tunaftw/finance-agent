#!/usr/bin/env python3
"""
Project future portfolio value for Investor AB based on historical returns.

Uses:
- Historical average return from 2015-2025
- Current portfolio as starting point
- Three deposit scenarios
- With and without 20% leverage (3% interest)
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

TICKER = "INVE-B.ST"

# Historical yearly deposits
YEARLY_DEPOSITS = {
    2015: 5200,
    2016: 56100,
    2017: 109000,
    2018: -65000,
    2019: 280000,
    2020: 212000,
    2021: 106866,
    2022: 50000,
    2023: 370000,
    2024: 342500,
    2025: 381000,
}

# Current portfolio values (from previous calculation)
CURRENT_PORTFOLIO_NO_LEVERAGE = 4_241_920
CURRENT_SHARES_NO_LEVERAGE = 12_936.63
CURRENT_PORTFOLIO_WITH_LEVERAGE = 4_725_301  # After paying debt with 3% interest
CURRENT_SHARES_WITH_LEVERAGE = 15_861.05
CURRENT_DEBT_WITH_INTEREST = 475_537  # Debt to pay back

def calculate_historical_returns():
    """Calculate historical average annual return and dividend yield."""
    print("Hämtar historisk data för Investor AB...")

    ticker = yf.Ticker(TICKER)
    hist = ticker.history(start="2015-01-01", end="2025-12-31", actions=True)

    # Price return (start of 2015 to end of 2025)
    start_price = hist['Close'].iloc[0]
    end_price = hist['Close'].iloc[-1]
    years = 11  # 2015-2025

    # Total price return (CAGR)
    price_cagr = (end_price / start_price) ** (1/years) - 1

    # Calculate dividend yield (average annual)
    total_dividends = hist['Dividends'].sum()
    avg_price = hist['Close'].mean()
    avg_dividend_per_year = total_dividends / years
    dividend_yield = avg_dividend_per_year / avg_price

    # Total return = price appreciation + dividend yield
    total_annual_return = price_cagr + dividend_yield

    print(f"\nHistorisk analys 2015-2025:")
    print(f"  Startpris (jan 2015): {start_price:.2f} SEK")
    print(f"  Slutpris (dec 2025): {end_price:.2f} SEK")
    print(f"  Prisökning (CAGR): {price_cagr*100:.1f}% per år")
    print(f"  Genomsnittlig utdelningsavkastning: {dividend_yield*100:.1f}% per år")
    print(f"  Total genomsnittlig årsavkastning: {total_annual_return*100:.1f}% per år")

    return {
        'price_cagr': price_cagr,
        'dividend_yield': dividend_yield,
        'total_return': total_annual_return,
        'current_price': end_price,
    }

def project_portfolio(
    starting_value: float,
    starting_shares: float,
    annual_return: float,
    dividend_yield: float,
    yearly_deposit: float,
    leverage: float,
    interest_rate: float,
    years: int,
    starting_price: float,
) -> pd.DataFrame:
    """
    Project portfolio value over time.

    Args:
        starting_value: Current portfolio value (net of any debt)
        starting_shares: Current number of shares
        annual_return: Expected annual total return
        dividend_yield: Expected dividend yield for reinvestment calc
        yearly_deposit: Annual new investment amount
        leverage: Leverage ratio (0.0 or 0.2)
        interest_rate: Annual interest rate on borrowed money
        years: Number of years to project
        starting_price: Current share price
    """
    results = []

    shares = starting_shares
    price = starting_price
    total_invested = sum(YEARLY_DEPOSITS.values())  # Historical
    total_borrowed = 0.0

    # For leveraged scenario, we start with existing debt
    if leverage > 0:
        # Approximate existing debt based on leverage ratio
        total_borrowed = total_invested * leverage * 1.1  # ~10% interest already accrued

    for year in range(years + 1):
        current_year = 2025 + year

        if year == 0:
            # Starting point
            portfolio_value = starting_value
        else:
            # Price appreciation
            price = price * (1 + annual_return - dividend_yield)

            # Dividend reinvestment
            dividend_per_share = price * dividend_yield
            dividend_received = shares * dividend_per_share

            # With leverage, dividends are also leveraged
            if leverage > 0:
                borrowed_for_div = dividend_received * leverage
                total_borrowed += borrowed_for_div
                dividend_to_invest = dividend_received + borrowed_for_div
            else:
                dividend_to_invest = dividend_received

            # Buy more shares with dividend
            new_shares_from_div = dividend_to_invest / price
            shares += new_shares_from_div

            # New yearly deposit (monthly, but simplified to yearly)
            if yearly_deposit > 0:
                borrowed_for_deposit = yearly_deposit * leverage
                total_to_invest = yearly_deposit + borrowed_for_deposit
                new_shares = total_to_invest / price
                shares += new_shares
                total_invested += yearly_deposit
                total_borrowed += borrowed_for_deposit

            # Interest on debt (compounds)
            if leverage > 0 and total_borrowed > 0:
                interest_cost = total_borrowed * interest_rate
                total_borrowed += interest_cost

            # Calculate net portfolio value
            gross_value = shares * price
            portfolio_value = gross_value - total_borrowed

        results.append({
            'year': current_year,
            'shares': shares,
            'price': price,
            'gross_value': shares * price,
            'debt': total_borrowed,
            'net_value': portfolio_value,
            'total_invested': total_invested,
        })

    return pd.DataFrame(results)

def main():
    print("=" * 70)
    print("INVESTOR AB - 10-ÅRIG FRAMTIDSPROJEKTION")
    print("=" * 70)

    # Get historical returns
    returns = calculate_historical_returns()

    # Calculate average deposit last 3 years
    last_3_years = [YEARLY_DEPOSITS[2023], YEARLY_DEPOSITS[2024], YEARLY_DEPOSITS[2025]]
    avg_deposit = sum(last_3_years) / 3

    print(f"\nInsättningar senaste 3 åren:")
    print(f"  2023: {YEARLY_DEPOSITS[2023]:,.0f} SEK")
    print(f"  2024: {YEARLY_DEPOSITS[2024]:,.0f} SEK")
    print(f"  2025: {YEARLY_DEPOSITS[2025]:,.0f} SEK")
    print(f"  Genomsnitt: {avg_deposit:,.0f} SEK/år")

    # Define scenarios
    deposit_scenarios = {
        'A': ('Fulla insättningar', avg_deposit),
        'B': ('Halva insättningar', avg_deposit / 2),
        'C': ('Inga nya insättningar', 0),
    }

    leverage_scenarios = {
        'Utan hävstång': (0.0, 0.0, CURRENT_PORTFOLIO_NO_LEVERAGE, CURRENT_SHARES_NO_LEVERAGE),
        'Med 20% hävstång (3% ränta)': (0.2, 0.03, CURRENT_PORTFOLIO_WITH_LEVERAGE, CURRENT_SHARES_WITH_LEVERAGE),
    }

    all_results = {}

    for deposit_name, (deposit_desc, yearly_deposit) in deposit_scenarios.items():
        print(f"\n{'=' * 70}")
        print(f"SCENARIO {deposit_name}: {deposit_desc.upper()} ({yearly_deposit:,.0f} SEK/år)")
        print("=" * 70)

        for leverage_name, (leverage, interest, starting_value, starting_shares) in leverage_scenarios.items():
            print(f"\n--- {leverage_name} ---")

            df = project_portfolio(
                starting_value=starting_value,
                starting_shares=starting_shares,
                annual_return=returns['total_return'],
                dividend_yield=returns['dividend_yield'],
                yearly_deposit=yearly_deposit,
                leverage=leverage,
                interest_rate=interest,
                years=10,
                starting_price=returns['current_price'],
            )

            key = f"{deposit_name}_{leverage_name}"
            all_results[key] = df

            # Print table
            print(f"\n{'År':<6} {'Aktier':>12} {'Pris':>10} {'Brutto':>14} {'Skuld':>12} {'NETTO':>14}")
            print("-" * 70)
            for _, row in df.iterrows():
                print(f"{int(row['year']):<6} {row['shares']:>12,.0f} {row['price']:>10,.0f} {row['gross_value']:>14,.0f} {row['debt']:>12,.0f} {row['net_value']:>14,.0f}")

    # Summary table
    print(f"\n{'=' * 70}")
    print("SAMMANFATTNING - PORTFÖLJVÄRDE OM 10 ÅR (2035)")
    print("=" * 70)

    print(f"\n{'Scenario':<35} {'Utan häv':>15} {'Med 20% häv':>15} {'Skillnad':>12}")
    print("-" * 80)

    for deposit_name, (deposit_desc, yearly_deposit) in deposit_scenarios.items():
        key_no_lev = f"{deposit_name}_Utan hävstång"
        key_lev = f"{deposit_name}_Med 20% hävstång (3% ränta)"

        val_no_lev = all_results[key_no_lev].iloc[-1]['net_value']
        val_lev = all_results[key_lev].iloc[-1]['net_value']
        diff = val_lev - val_no_lev

        label = f"{deposit_name}. {deposit_desc} ({yearly_deposit/1000:.0f}k/år)"
        print(f"{label:<35} {val_no_lev:>15,.0f} {val_lev:>15,.0f} {diff:>+12,.0f}")

    # Print key assumptions
    print(f"\n{'=' * 70}")
    print("ANTAGANDEN")
    print("=" * 70)
    print(f"  Förväntad årlig totalavkastning: {returns['total_return']*100:.1f}%")
    print(f"    - Prisökning: {returns['price_cagr']*100:.1f}%")
    print(f"    - Utdelning: {returns['dividend_yield']*100:.1f}%")
    print(f"  Hävstångsränta: 3% per år (sammansatt)")
    print(f"  Alla utdelningar återinvesteras")
    print(f"  Insättningar görs årligen")

    return all_results

if __name__ == "__main__":
    results = main()
