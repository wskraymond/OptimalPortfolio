from datetime import datetime
import time
import traceback
from data.model.daily_price import Currency, Stock
import pandas as pd
from data.store import Store
from ibapi.contract import Contract
from ibapi.client import *
from ibapi.wrapper import *
import requests

store_host = 'host.docker.internal'
store = Store(hosts=[store_host], keyspace='store')

def pre_start_init():
    print("Initializing resources...")

    US_benchmark = 'VOO'
    QQQ_benchmark = 'QQQ'
    TW_benchmark = 'EWT'
    JP_benchmark = '1329.T'
    HK_benchmark = '2800.HK'
    CN_benchmark = '159919.SZ'
    Gold = 'IAU'
    BTC = 'IBIT'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise an error for HTTP issues
    sp_table = pd.read_html(response.text)
    sp_df = sp_table[0]
    tickers = set(sp_df['Symbol'].to_list())
    benchmarks = [US_benchmark, QQQ_benchmark, TW_benchmark, JP_benchmark, HK_benchmark, CN_benchmark, Gold, BTC]
    tickers = list(tickers)

    SP_list = []
    # add tickers to contractList following the same format as above, with exchange = SMART and currency = USD
    for ticker in tickers:
        contract = Contract()
        if '.' in ticker:
            contract.symbol = ticker.replace('.', ' ')
        else:
            contract.symbol = ticker
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        SP_list.append(contract)

    ETF_list = []
    for ticker in benchmarks: ## according to the suffix of the ticker, we can set the exchange and currency
        contract = Contract()
        if '.' in ticker:
            contract.symbol = ticker.split('.')[0]
        else:
            contract.symbol = ticker
        contract.secType = "STK"
        if ticker.endswith('.T'):
            contract.exchange = "SMART"
            contract.currency = "JPY"
        elif ticker.endswith('.HK'):
            contract.exchange = "SMART"
            contract.currency = "HKD"
        elif ticker.endswith('.SZ'):
            contract.exchange = "SMART"
            contract.currency = "CNY"
        else:
            contract.exchange = "SMART"
            contract.currency = "USD"
        ETF_list.append(contract)


    print("contractList=", SP_list + ETF_list)
    return {"S&P": SP_list, "Benchmark": ETF_list} # in order to save in different buckets in the store

# Example usage
if __name__ == "__main__":
    m = pre_start_init()
    for bucket, contracts in m.items():
        store.save_contract_list(contracts, bucket=bucket)