from datetime import datetime
import os
import time
import traceback
from data.model.my_model import Currency, Stock
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
    print(f"Current directory: {os.getcwd()}")
    csv_path = 'csv/etf_list.csv'
    print(f"CSV path: {os.path.abspath(csv_path)}")

    # read symbols 
    df = pd.read_csv(csv_path)
    tickers = set(df['Ticker'].to_list())
    print("tickers=", tickers)

    ETF_list = []
    # add tickers to contractList following the same format as above, with exchange = SMART and currency = USD
    for ticker in tickers:
        contract = Contract()
        if '.' in ticker:
            contract.symbol = ticker.replace('.', ' ')
        elif not ticker.isalpha(): 
            contract.symbol = ticker
        else:
            contract.symbol = ticker
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        ETF_list.append(contract)

    print("contractList=", ETF_list)

    return {'ETF': ETF_list}

if __name__ == "__main__":
    m = pre_start_init()
    for bucket, contracts in m.items():
        store.save_contract_list(contracts, bucket=bucket)