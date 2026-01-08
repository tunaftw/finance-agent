#!/usr/bin/env python3
"""
Calculate portfolio value for Investor AB based on yearly deposits.

This script:
1. Fetches historical price and dividend data for Investor AB (INVE-B.ST)
2. Simulates monthly deposits (equal amounts each month)
3. Reinvests all dividends
4. Calculates final portfolio value with and without leverage
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Yearly deposits from the image (SEK)
# Note: 2018 has a withdrawal of -65,000
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

TICKER = "INVE-B.ST"

def fetch_data():
    """Fetch historical price and dividend data from Yahoo Finance."""
    print(f"Fetching data for {TICKER}...")

    ticker = yf.Ticker(TICKER)

    # Get historical prices from 2015-01-01 to today
    start_date = "2015-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")

    # Get price history
    hist = ticker.history(start=start_date, end=end_date, actions=True)

    print(f"Fetched {len(hist)} trading days of data")
    print(f"Date range: {hist.index.min()} to {hist.index.max()}")

    # Check dividends
    dividends = hist[hist['Dividends'] > 0]['Dividends']
    print(f"\nFound {len(dividends)} dividend payments:")
    for date, div in dividends.items():
        print(f"  {date.strftime('%Y-%m-%d')}: {div:.2f} SEK")

    return hist

def get_price_on_date(hist: pd.DataFrame, date) -> float:
    """Get the closing price on or before a specific date."""
    # Convert to timezone-aware timestamp if needed
    if isinstance(date, datetime):
        date_ts = pd.Timestamp(date)
        if date_ts.tz is None:
            date_ts = date_ts.tz_localize('Europe/Stockholm')
    else:
        date_ts = date

    # Normalize to start of day
    date_only = date_ts.normalize()

    # Get all dates on or before the target
    available = hist.index[hist.index <= date_only]

    if len(available) == 0:
        # If no data before this date, use first available
        return hist['Close'].iloc[0]

    return hist.loc[available[-1], 'Close']

def calculate_portfolio(hist: pd.DataFrame, leverage: float = 0.0) -> dict:
    """
    Calculate portfolio value with monthly deposits and dividend reinvestment.

    Args:
        hist: Historical price data with dividends
        leverage: Leverage ratio (0.0 = no leverage, 0.2 = 20% leverage)

    Returns:
        Dictionary with portfolio details
    """
    shares = 0.0
    total_invested = 0.0
    total_dividends = 0.0
    monthly_log = []

    # Process each year
    for year, annual_amount in YEARLY_DEPOSITS.items():
        monthly_amount = annual_amount / 12

        for month in range(1, 13):
            # Date is first of month
            deposit_date = datetime(year, month, 1)

            # Skip future dates
            if deposit_date > datetime.now():
                break

            try:
                price = get_price_on_date(hist, deposit_date)
            except:
                continue

            if price <= 0:
                continue

            # Calculate effective investment with leverage
            effective_amount = monthly_amount * (1 + leverage)

            # Buy shares with the monthly amount
            if effective_amount > 0:
                new_shares = effective_amount / price
                shares += new_shares
                total_invested += monthly_amount  # Track actual money invested
            elif effective_amount < 0:
                # Withdrawal - sell shares proportionally
                shares_to_sell = abs(effective_amount) / price
                shares -= min(shares_to_sell, shares)  # Can't sell more than we have
                total_invested += monthly_amount  # This is negative, so reduces total

            # Check for dividends this month
            month_start = deposit_date
            month_end = deposit_date + relativedelta(months=1)

            # Get dividends in this month
            dividends_this_month = hist[
                (hist.index >= pd.Timestamp(month_start)) &
                (hist.index < pd.Timestamp(month_end)) &
                (hist['Dividends'] > 0)
            ]

            for div_date, row in dividends_this_month.iterrows():
                dividend_per_share = row['Dividends']
                dividend_received = shares * dividend_per_share * (1 + leverage)
                total_dividends += shares * dividend_per_share  # Track without leverage

                # Reinvest dividend
                div_price = get_price_on_date(hist, div_date.to_pydatetime())
                if div_price > 0:
                    new_shares_from_div = dividend_received / div_price
                    shares += new_shares_from_div

            monthly_log.append({
                'date': deposit_date,
                'shares': shares,
                'price': price,
                'monthly_deposit': monthly_amount,
                'portfolio_value': shares * price / (1 + leverage) if leverage > 0 else shares * price
            })

    # Get current price
    current_price = hist['Close'].iloc[-1]

    # For leveraged portfolio, we need to account for the debt
    if leverage > 0:
        # Total value of shares (leveraged)
        gross_value = shares * current_price
        # Debt = leverage * total_invested
        debt = leverage * total_invested
        # Net value after paying back debt
        final_value = gross_value - debt
    else:
        final_value = shares * current_price

    return {
        'shares': shares,
        'current_price': current_price,
        'total_invested': total_invested,
        'total_dividends': total_dividends,
        'final_value': final_value,
        'gross_value': shares * current_price,
        'leverage': leverage,
        'debt': leverage * total_invested if leverage > 0 else 0,
        'monthly_log': monthly_log
    }

def calculate_portfolio_v2(hist: pd.DataFrame, leverage: float = 0.0, annual_interest_rate: float = 0.0) -> dict:
    """
    More accurate calculation with proper leverage accounting.

    With leverage:
    - Each month, we invest X SEK of our own money
    - We borrow X * leverage additional SEK
    - So we buy shares worth X * (1 + leverage)
    - The debt grows with each deposit
    - Interest accrues on outstanding debt
    - At the end, we sell everything and pay back the debt + interest
    """
    shares = 0.0
    total_own_invested = 0.0
    dividend_log = []

    # Track individual loans with their dates for interest calculation
    loans = []  # List of (date, principal_amount)

    # Create a timeline of all deposits and dividends
    events = []

    # Add monthly deposits
    for year, annual_amount in YEARLY_DEPOSITS.items():
        monthly_amount = annual_amount / 12
        for month in range(1, 13):
            deposit_date = datetime(year, month, 1)
            if deposit_date > datetime.now():
                break
            events.append({
                'date': pd.Timestamp(deposit_date).tz_localize('Europe/Stockholm'),
                'type': 'deposit',
                'amount': monthly_amount
            })

    # Add dividends
    dividends = hist[hist['Dividends'] > 0][['Dividends']]
    for div_date, row in dividends.iterrows():
        events.append({
            'date': div_date,  # Already timezone-aware
            'type': 'dividend',
            'per_share': row['Dividends']
        })

    # Sort events by date
    events.sort(key=lambda x: x['date'])

    # Process events chronologically
    for event in events:
        date = event['date']

        try:
            price = get_price_on_date(hist, date)
        except:
            continue

        if price <= 0:
            continue

        if event['type'] == 'deposit':
            amount = event['amount']

            # Calculate borrowed amount
            borrowed = amount * leverage
            total_amount = amount + borrowed

            if total_amount > 0:
                new_shares = total_amount / price
                shares += new_shares
                total_own_invested += amount
                if borrowed > 0:
                    loans.append((date, borrowed))
            elif total_amount < 0:
                # Withdrawal - sell shares, pay back proportional debt
                shares_to_sell = abs(total_amount) / price
                shares -= min(shares_to_sell, shares)
                total_own_invested += amount  # Negative
                if borrowed < 0:
                    loans.append((date, borrowed))  # Negative = paying back

        elif event['type'] == 'dividend':
            if shares > 0:
                dividend_per_share = event['per_share']
                dividend_received = shares * dividend_per_share
                dividend_log.append({
                    'date': date,
                    'shares': shares,
                    'per_share': dividend_per_share,
                    'total': dividend_received
                })

                # Reinvest dividend (also with leverage)
                borrowed_for_div = dividend_received * leverage
                total_to_invest = dividend_received + borrowed_for_div

                new_shares = total_to_invest / price
                shares += new_shares
                if borrowed_for_div > 0:
                    loans.append((date, borrowed_for_div))

    # Get final values
    current_price = hist['Close'].iloc[-1]
    gross_value = shares * current_price

    # Calculate total debt with interest
    end_date = hist.index[-1]
    total_principal = 0.0
    total_with_interest = 0.0

    for loan_date, principal in loans:
        total_principal += principal

        # Calculate years between loan date and end date
        days = (end_date - loan_date).days
        years = days / 365.25

        # Compound interest: A = P * (1 + r)^t
        if annual_interest_rate > 0:
            amount_with_interest = principal * ((1 + annual_interest_rate) ** years)
        else:
            amount_with_interest = principal

        total_with_interest += amount_with_interest

    # Pay back all debt with interest
    net_value = gross_value - total_with_interest

    return {
        'shares': shares,
        'current_price': current_price,
        'total_own_invested': total_own_invested,
        'total_borrowed_principal': total_principal,
        'total_debt_with_interest': total_with_interest,
        'total_interest_paid': total_with_interest - total_principal,
        'gross_value': gross_value,
        'net_value': net_value,
        'leverage': leverage,
        'annual_interest_rate': annual_interest_rate,
        'total_dividends': sum(d['total'] for d in dividend_log),
        'dividend_log': dividend_log
    }

def main():
    print("=" * 60)
    print("INVESTOR AB PORTFOLIO CALCULATION")
    print("=" * 60)

    # Fetch data
    hist = fetch_data()

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

    # Calculate without leverage
    print("\n" + "=" * 60)
    print("SCENARIO 1: NO LEVERAGE")
    print("=" * 60)
    result1 = calculate_portfolio_v2(hist, leverage=0.0, annual_interest_rate=0.0)

    print(f"Total shares owned: {result1['shares']:,.4f}")
    print(f"Current price (INVE-B.ST): {result1['current_price']:,.2f} SEK")
    print(f"Total own money invested: {result1['total_own_invested']:,.0f} SEK")
    print(f"Total dividends received (reinvested): {result1['total_dividends']:,.0f} SEK")
    print(f"")
    print(f">>> TOTAL PORTFOLIO VALUE: {result1['net_value']:,.0f} SEK <<<")
    print(f"")
    print(f"Profit: {result1['net_value'] - result1['total_own_invested']:,.0f} SEK")
    print(f"Return: {((result1['net_value'] / result1['total_own_invested']) - 1) * 100:.1f}%")

    # Calculate with 20% leverage, no interest
    print("\n" + "=" * 60)
    print("SCENARIO 2: 20% LEVERAGE (0% ränta)")
    print("=" * 60)
    result2 = calculate_portfolio_v2(hist, leverage=0.2, annual_interest_rate=0.0)

    print(f"Total shares owned: {result2['shares']:,.4f}")
    print(f"Current price (INVE-B.ST): {result2['current_price']:,.2f} SEK")
    print(f"Total own money invested: {result2['total_own_invested']:,.0f} SEK")
    print(f"Total borrowed (principal): {result2['total_borrowed_principal']:,.0f} SEK")
    print(f"Gross portfolio value: {result2['gross_value']:,.0f} SEK")
    print(f"Debt to pay back: {result2['total_debt_with_interest']:,.0f} SEK")
    print(f"")
    print(f">>> TOTAL PORTFOLIO VALUE (after paying debt): {result2['net_value']:,.0f} SEK <<<")
    print(f"")
    print(f"Profit: {result2['net_value'] - result2['total_own_invested']:,.0f} SEK")
    print(f"Return on own capital: {((result2['net_value'] / result2['total_own_invested']) - 1) * 100:.1f}%")

    # Calculate with 20% leverage, 3% interest
    print("\n" + "=" * 60)
    print("SCENARIO 3: 20% LEVERAGE (3% ränta)")
    print("=" * 60)
    result3 = calculate_portfolio_v2(hist, leverage=0.2, annual_interest_rate=0.03)

    print(f"Total shares owned: {result3['shares']:,.4f}")
    print(f"Current price (INVE-B.ST): {result3['current_price']:,.2f} SEK")
    print(f"Total own money invested: {result3['total_own_invested']:,.0f} SEK")
    print(f"Total borrowed (principal): {result3['total_borrowed_principal']:,.0f} SEK")
    print(f"Total interest cost: {result3['total_interest_paid']:,.0f} SEK")
    print(f"Total debt with interest: {result3['total_debt_with_interest']:,.0f} SEK")
    print(f"Gross portfolio value: {result3['gross_value']:,.0f} SEK")
    print(f"")
    print(f">>> TOTAL PORTFOLIO VALUE (after paying debt + interest): {result3['net_value']:,.0f} SEK <<<")
    print(f"")
    print(f"Profit: {result3['net_value'] - result3['total_own_invested']:,.0f} SEK")
    print(f"Return on own capital: {((result3['net_value'] / result3['total_own_invested']) - 1) * 100:.1f}%")

    # Summary comparison
    print("\n" + "=" * 60)
    print("SAMMANFATTNING")
    print("=" * 60)
    print(f"Insatt kapital:           {result1['total_own_invested']:>12,.0f} SEK")
    print(f"")
    print(f"Scenario 1 (utan hävstång):     {result1['net_value']:>12,.0f} SEK  (+{result1['net_value'] - result1['total_own_invested']:,.0f})")
    print(f"Scenario 2 (20% hävstång, 0%):  {result2['net_value']:>12,.0f} SEK  (+{result2['net_value'] - result2['total_own_invested']:,.0f})")
    print(f"Scenario 3 (20% hävstång, 3%):  {result3['net_value']:>12,.0f} SEK  (+{result3['net_value'] - result3['total_own_invested']:,.0f})")

    return result1, result2, result3

if __name__ == "__main__":
    result1, result2, result3 = main()
