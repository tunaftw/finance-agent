#!/usr/bin/env python3
"""
Calculate portfolio value for Avanza Zero based on yearly deposits.

This script:
1. Uses historical NAV data for Avanza Zero from Avanza API
2. Simulates monthly deposits (equal amounts each month)
3. NO dividend reinvestment needed - Avanza Zero is an accumulating fund
   (dividends are automatically reinvested in the NAV)
4. Calculates final portfolio value with and without leverage
"""

import json
import pandas as pd
from datetime import datetime
from pathlib import Path

# Yearly deposits from the image (SEK)
YEARLY_DEPOSITS = {
    2015: 5200,
    2016: 56100,
    2017: 109000,
    2018: -65000,  # Withdrawal
    2019: 280000,
    2020: 212000,
    2021: 106866,
    2022: 50000,
    2023: 370000,
    2024: 342500,
    2025: 381000,
}

def load_avanza_zero_data() -> pd.DataFrame:
    """Load Avanza Zero NAV data from JSON file."""
    data_file = Path("data/prices/avanza_zero_history.json")

    with open(data_file) as f:
        data = json.load(f)

    # Convert to DataFrame
    records = []
    for item in data['ohlc']:
        records.append({
            'timestamp': datetime.fromtimestamp(item['timestamp'] / 1000),
            'close': item['close'],
            'open': item.get('open', item['close']),
            'high': item.get('high', item['close']),
            'low': item.get('low', item['close']),
        })

    df = pd.DataFrame(records)
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)

    return df

def get_price_on_date(df: pd.DataFrame, date: datetime) -> float:
    """Get the NAV on or before a specific date."""
    # Find dates on or before target
    available = df.index[df.index <= date]

    if len(available) == 0:
        return df['close'].iloc[0]

    return df.loc[available[-1], 'close']

def calculate_portfolio(df: pd.DataFrame, leverage: float = 0.0, annual_interest_rate: float = 0.0) -> dict:
    """
    Calculate portfolio value with monthly deposits.

    Note: Avanza Zero is an accumulating fund - no dividend processing needed.
    The NAV already includes reinvested dividends.
    """
    shares = 0.0  # Fund units
    total_own_invested = 0.0
    loans = []  # Track borrowed amounts for interest calculation

    # Process monthly deposits
    for year, annual_amount in YEARLY_DEPOSITS.items():
        monthly_amount = annual_amount / 12

        for month in range(1, 13):
            deposit_date = datetime(year, month, 1)

            # Skip future dates
            if deposit_date > datetime.now():
                break

            try:
                nav = get_price_on_date(df, deposit_date)
            except:
                continue

            if nav <= 0:
                continue

            # Calculate borrowed amount
            borrowed = monthly_amount * leverage
            total_amount = monthly_amount + borrowed

            if total_amount > 0:
                new_units = total_amount / nav
                shares += new_units
                total_own_invested += monthly_amount
                if borrowed > 0:
                    loans.append((deposit_date, borrowed))
            elif total_amount < 0:
                # Withdrawal - sell units
                units_to_sell = abs(total_amount) / nav
                shares -= min(units_to_sell, shares)
                total_own_invested += monthly_amount  # Negative
                if borrowed < 0:
                    loans.append((deposit_date, borrowed))

    # Get final NAV
    current_nav = df['close'].iloc[-1]
    gross_value = shares * current_nav

    # Calculate total debt with interest
    end_date = df.index[-1]
    total_principal = 0.0
    total_with_interest = 0.0

    for loan_date, principal in loans:
        total_principal += principal

        # Calculate years between loan date and end date
        days = (end_date - loan_date).days
        years = days / 365.25

        # Compound interest
        if annual_interest_rate > 0:
            amount_with_interest = principal * ((1 + annual_interest_rate) ** years)
        else:
            amount_with_interest = principal

        total_with_interest += amount_with_interest

    net_value = gross_value - total_with_interest

    return {
        'units': shares,
        'current_nav': current_nav,
        'total_own_invested': total_own_invested,
        'total_borrowed_principal': total_principal,
        'total_debt_with_interest': total_with_interest,
        'total_interest_paid': total_with_interest - total_principal,
        'gross_value': gross_value,
        'net_value': net_value,
        'leverage': leverage,
        'annual_interest_rate': annual_interest_rate,
    }

def main():
    print("=" * 60)
    print("AVANZA ZERO PORTFOLIO CALCULATION")
    print("=" * 60)

    # Load data
    print("\nLoading Avanza Zero NAV data...")
    df = load_avanza_zero_data()

    print(f"Data range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
    print(f"Data points: {len(df)}")
    print(f"First NAV: {df['close'].iloc[0]:.2f} SEK")
    print(f"Latest NAV: {df['close'].iloc[-1]:.2f} SEK")

    # Note about dividends
    print("\nNOTE: Avanza Zero är en ackumulerande fond.")
    print("      Utdelningar återinvesteras automatiskt i NAV-kursen.")
    print("      Ingen separat utdelningshantering behövs.")

    # Print summary of deposits
    print("\n" + "=" * 60)
    print("YEARLY DEPOSITS")
    print("=" * 60)
    total = 0
    for year, amount in YEARLY_DEPOSITS.items():
        total += amount
        print(f"{year}: {amount:>10,.0f} SEK")
    print("-" * 30)
    print(f"Total: {total:>10,.0f} SEK")

    # Scenario 1: No leverage
    print("\n" + "=" * 60)
    print("SCENARIO 1: UTAN HÄVSTÅNG")
    print("=" * 60)
    result1 = calculate_portfolio(df, leverage=0.0, annual_interest_rate=0.0)

    print(f"Fondandelar: {result1['units']:,.4f}")
    print(f"Aktuellt NAV: {result1['current_nav']:,.2f} SEK")
    print(f"Totalt eget insatt: {result1['total_own_invested']:,.0f} SEK")
    print(f"")
    print(f">>> TOTALT PORTFÖLJVÄRDE: {result1['net_value']:,.0f} SEK <<<")
    print(f"")
    print(f"Vinst: {result1['net_value'] - result1['total_own_invested']:,.0f} SEK")
    print(f"Avkastning: {((result1['net_value'] / result1['total_own_invested']) - 1) * 100:.1f}%")

    # Scenario 2: 20% leverage, 0% interest
    print("\n" + "=" * 60)
    print("SCENARIO 2: 20% HÄVSTÅNG (0% ränta)")
    print("=" * 60)
    result2 = calculate_portfolio(df, leverage=0.2, annual_interest_rate=0.0)

    print(f"Fondandelar: {result2['units']:,.4f}")
    print(f"Aktuellt NAV: {result2['current_nav']:,.2f} SEK")
    print(f"Totalt eget insatt: {result2['total_own_invested']:,.0f} SEK")
    print(f"Totalt lånat (principal): {result2['total_borrowed_principal']:,.0f} SEK")
    print(f"Brutto portföljvärde: {result2['gross_value']:,.0f} SEK")
    print(f"Skuld att återbetala: {result2['total_debt_with_interest']:,.0f} SEK")
    print(f"")
    print(f">>> TOTALT PORTFÖLJVÄRDE (efter skuld): {result2['net_value']:,.0f} SEK <<<")
    print(f"")
    print(f"Vinst: {result2['net_value'] - result2['total_own_invested']:,.0f} SEK")
    print(f"Avkastning på eget kapital: {((result2['net_value'] / result2['total_own_invested']) - 1) * 100:.1f}%")

    # Scenario 3: 20% leverage, 3% interest
    print("\n" + "=" * 60)
    print("SCENARIO 3: 20% HÄVSTÅNG (3% ränta)")
    print("=" * 60)
    result3 = calculate_portfolio(df, leverage=0.2, annual_interest_rate=0.03)

    print(f"Fondandelar: {result3['units']:,.4f}")
    print(f"Aktuellt NAV: {result3['current_nav']:,.2f} SEK")
    print(f"Totalt eget insatt: {result3['total_own_invested']:,.0f} SEK")
    print(f"Totalt lånat (principal): {result3['total_borrowed_principal']:,.0f} SEK")
    print(f"Räntekostnad (sammansatt): {result3['total_interest_paid']:,.0f} SEK")
    print(f"Total skuld med ränta: {result3['total_debt_with_interest']:,.0f} SEK")
    print(f"Brutto portföljvärde: {result3['gross_value']:,.0f} SEK")
    print(f"")
    print(f">>> TOTALT PORTFÖLJVÄRDE (efter skuld + ränta): {result3['net_value']:,.0f} SEK <<<")
    print(f"")
    print(f"Vinst: {result3['net_value'] - result3['total_own_invested']:,.0f} SEK")
    print(f"Avkastning på eget kapital: {((result3['net_value'] / result3['total_own_invested']) - 1) * 100:.1f}%")

    # Summary
    print("\n" + "=" * 60)
    print("SAMMANFATTNING - AVANZA ZERO")
    print("=" * 60)
    print(f"Insatt kapital:                    {result1['total_own_invested']:>12,.0f} SEK")
    print(f"")
    print(f"Scenario 1 (utan hävstång):        {result1['net_value']:>12,.0f} SEK  (+{result1['net_value'] - result1['total_own_invested']:,.0f})")
    print(f"Scenario 2 (20% hävstång, 0%):     {result2['net_value']:>12,.0f} SEK  (+{result2['net_value'] - result2['total_own_invested']:,.0f})")
    print(f"Scenario 3 (20% hävstång, 3%):     {result3['net_value']:>12,.0f} SEK  (+{result3['net_value'] - result3['total_own_invested']:,.0f})")

    return result1, result2, result3

if __name__ == "__main__":
    result1, result2, result3 = main()
