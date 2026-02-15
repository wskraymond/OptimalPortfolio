from datetime import datetime
import time
import traceback
import pandas as pd
from data.store import Store
from data.model.my_model import Fund, Dividend
import yfinance as yf
from yahooquery import Ticker
from ibapi.contract import Contract
from data.contract.MyContract import contractList

store_host = 'host.docker.internal'
store = Store(hosts=[store_host], keyspace='store')

def load_div_expense_to_store(contract_list, from_date):
    """
    Load dividend and fund expense ratio data into Cassandra store.

    Args:
        contract_list (list): List of contract objects with `symbol` attribute.
        from_date (str): Start date for filtering dividend data.
    """
    symbols = [contract.symbol for contract in contract_list]
    print("Fetching expense ratios and dividends for symbols:", symbols)

    for contract in contract_list:
        try:
            symbol = contract.symbol
            print(f"Processing {symbol}")

            # Fetch and load dividend data
            div = safe_get_dividends(symbol)
            for date, amount in div.items():
                if date >= pd.to_datetime(from_date):
                    store.insert_dividend(
                        ticker=symbol,
                        date=date,
                        amount=amount
                    )

            # Fetch and load fund expense ratio
            expense_ratio = get_expense_ratio(symbol)
            store.insert_fund(
                ticker=symbol,
                expense_ratio=expense_ratio
            )

            time.sleep(1)  # Avoid rate-limiting

        except Exception as error:
            print("An error occurred:", error)
            traceback.print_exc()
            print("symbol=", contract.symbol, "cannot be resolved")

def safe_get_dividends(symbol, retries=3, delay=2):
    """
    Safely fetch dividend data with retries.

    Args:
        symbol (str): Ticker symbol.
        retries (int): Number of retry attempts.
        delay (int): Delay between retries in seconds.

    Returns:
        pd.Series: Dividend data as a Pandas Series.
    """
    for attempt in range(retries):
        try:
            corp_action = yf.Ticker(symbol)
            div = corp_action.get_dividends()
            if not div.empty:
                div.index = div.index.tz_localize(None)  # Remove timezone info
            return div
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for {symbol}: {e}")
            time.sleep(delay)
            delay *= 2  # Exponential backoff

    return pd.Series()

def get_expense_ratio(symbol) -> float:
    """
    Fetch the expense ratio for a given symbol.

    Args:
        symbol (str): Ticker symbol.
        etfs (Ticker): YahooQuery Ticker object.

    Returns:
        float: Expense ratio, or 0.0 if not available.
    """
    try:
        # Fetch ETF data using YahooQuery
        etf = Ticker(symbol)
        if symbol in etf.fund_profile and 'feesExpensesInvestment' in etf.fund_profile[symbol]:
            return etf.fund_profile[symbol]['feesExpensesInvestment'].get('annualReportExpenseRatio', 0.0)
    except Exception as e:
        print(f"Failed to fetch expense ratio for {symbol}: {e}")



    return 0.0

# Create contract from portfolio row
def create_contract_from_portfolio_row(row):
    contract = Contract()
    contract.symbol = row.name  # 'ticker' is set as index in DataFrame
    contract.secType = "STK"
    contract.currency = row['currency']['code']
    return contract

def pre_start_init():
    print("Initializing resources...")
    # Append first portfolio contract to global list
    global contractList
    contractList.extend(store.select_all_stocks_in_contract())

    print("contractList=", contractList)
    # Load config, connect to DB, etc.

# Example usage
if __name__ == "__main__":
    pre_start_init()
    from_date = "2010-01-01"

    load_div_expense_to_store(contractList, from_date)