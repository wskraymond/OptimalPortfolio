import time
import pandas as pd
import numpy as np
import pandas_datareader as pdr
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
import datetime as dt
import seaborn as sns
from pandas.core.window import Window
from scipy.optimize import minimize
from argparse import ArgumentParser
import math
from pandas_datareader.data import DataReader as dr
import traceback

from data.contract.MyContract import contractList
from data.store import Store
from datetime import datetime
import mplcursors
import yfinance as yf
from yahooquery import Ticker
from ibapi.contract import Contract
from scipy import stats as ss

store_host = 'host.docker.internal'

# Create contract from portfolio row
def create_contract_from_portfolio_row(row):
    contract = Contract()
    contract.symbol = row.name  # 'ticker' is set as index in DataFrame
    contract.secType = "STK"
    contract.currency = row['currency']['code']
    return contract

class Stats():
    def __init__(self, startdate, holdingPeriodYear, rollingYr, divTaxRate):
        self.TRADING_DAYS = 252
        self.holdingPeriodYear = holdingPeriodYear
        self.no_of_days = self.TRADING_DAYS * self.holdingPeriodYear  # number of days for a quarter = 63
        self.fromDate = datetime.strptime(startdate, '%d/%m/%Y').date()
        self.Closeprice = pd.DataFrame()
        self.div = pd.DataFrame()
        self.expense_ratio = pd.Series()
        self.yc = None
        self.returns = None
        self.div_return = None
        self.log_expense = None
        self.recvTickers = []
        self.divTaxRate = divTaxRate
        self.rollingYr = rollingYr
        self.windowSize = self.TRADING_DAYS * rollingYr
        self.store = Store(hosts=[store_host], keyspace='store')
        # Append first portfolio contract to global list
        global contractList
        portfolio_list = self.store.select_portfolio_in_pd()
        if not portfolio_list.empty:
            for _, row in portfolio_list.iterrows():
                contract = create_contract_from_portfolio_row(row)
                contractList.append(contract)


        print("contractList=", contractList)

    def loadYC(self):
        syms = ['DGS30', 'DGS20', 'DGS10', 'DGS5', 'DGS2', 'DGS1', 'DGS1MO', 'DGS3MO']
        yc = dr(syms, 'fred', self.fromDate, dt.date.today())  # could specify start date with start param here
        names = dict(zip(syms, ['30yr', '20yr', '10yr', '5yr', '2yr', '1yr', '1m', '3m']))
        yc = yc.rename(columns=names)
        yc = yc[['1m', '3m', '1yr', '2yr', '5yr', '10yr', '20yr', '30yr']]
        yc.index = pd.to_datetime(yc.index)
        # print(yc)
        self.yc = yc

    """ def get_expense_ratio(self, ticker, etf):
        if ticker in etf.fund_profile and 'feesExpensesInvestment' in etf.fund_profile[
            ticker] and 'annualReportExpenseRatio' in etf.fund_profile[ticker]['feesExpensesInvestment']:
            # Both columns exist
            expense_ratio = etf.fund_profile[ticker]['feesExpensesInvestment']['annualReportExpenseRatio']
        else:
            # Either or both columns do not exist
            expense_ratio = 0.0
        return expense_ratio """
    
    def get_expense_ratio(self, ticker, etf):
        try:
            return etf.fund_profile[ticker]['feesExpensesInvestment']['annualReportExpenseRatio']
        except (KeyError, TypeError):
            return 0.0


    def loadDailyPrice(self):
        global contractList
        for i in contractList:
            try:
                print(i.symbol)
                rows = self.store.select_daily_price_in_pd_by_range(ticker=i.symbol,
                                                               fromDate=self.fromDate,
                                                               toDate=dt.date.today())
                self.Closeprice[i.symbol] = rows['close']
                self.recvTickers.append(i.symbol)
            except Exception as error:
                print("An error occurred:", error)
                traceback.print_exc()
                print("symbol=", i.symbol, " cannot be resolved")
        # https://pandas.pydata.org/docs/user_guide/timeseries.html
        self.Closeprice.index = pd.to_datetime(self.Closeprice.index).tz_localize(None)

    """ def load_div_expense(self):
        self.div = pd.DataFrame(index=self.Closeprice.index)
        for i in contractList:
            try:
                print(i.symbol)
                corp_action = yf.Ticker(i.symbol)
                div = corp_action.get_dividends()
                if not div.empty:
                    div.index = div.index.tz_localize(None)
                self.div[i.symbol] = div
                etf = Ticker(i.symbol)
                self.expense_ratio.loc[i.symbol] = self.get_expense_ratio(i.symbol, etf)
                time.sleep(3)  # to avoid being rate limited by yahoo
            except Exception as error:
                print("An error occurred:", error)
                traceback.print_exc()
                print("symbol=", i.symbol, " cannot be resolved")
        # https://pandas.pydata.org/docs/user_guide/timeseries.html
        self.div = self.div[pd.to_datetime(self.fromDate) <= self.div.index]
        self.div = self.div.fillna(0.0) """

    def safe_get_dividends(self, symbol, retries=3, delay=2):
        for attempt in range(retries):
            try:
                div = yf.Ticker(symbol).get_dividends()
                if not div.empty:
                    div.index = div.index.tz_localize(None)
                return div
            except Exception as e:
                print(f"Retry {attempt+1} for {symbol}: {e}")
                time.sleep(delay)
                delay *= 2
        return pd.Series()


    def load_div_expense(self):
        global contractList
        self.div = pd.DataFrame(index=self.Closeprice.index)
        symbols = [i.symbol for i in contractList]
        print("Fetching expense ratios for symbols:", symbols)
        etfs = Ticker(" ".join(symbols))

        for i in contractList:
            try:
                print(f"Processing {i.symbol}")
                div = self.safe_get_dividends(i.symbol)
                self.div[i.symbol] = div
                self.expense_ratio.loc[i.symbol] = self.get_expense_ratio(i.symbol, etfs)
                time.sleep(1)
            except Exception as error:
                print("An error occurred:", error)
                traceback.print_exc()
                print("symbol=", i.symbol, " cannot be resolved")

        self.div = self.div[self.div.index >= pd.to_datetime(self.fromDate)]
        self.div = self.div.fillna(0.0)


    def pre_return(self):
        # calculate the log return
        # returns is a dataframe class
        self.returns = np.log(self.Closeprice / self.Closeprice.shift(1))
        return self.returns

    def after_tax(self):
        self.div = np.multiply(self.div, 1 - self.divTaxRate)

    def pre_div_return(self):
        self.div_return = np.log(1 + self.div / self.Closeprice).fillna(0.0)
        return self.div_return

    def pre_log_expense(self):
        self.log_expense = np.log(1 - self.expense_ratio)
        return self.log_expense

    # window operation doc
    # https://pandas.pydata.org/docs/reference/window.html

    # rolling apply to specific function
    # https://pandas.pydata.org/docs/user_guide/window.html#rolling-apply

    # https://pandas.pydata.org/docs/user_guide/window.html#computing-rolling-pairwise-covariances-and-correlations
    # rolling window operation

    def rolling_return_list(self):
        # Also known as rolling or moving window,
        # the window slides across all dimensions of the array and extracts subsets of the array at all window positions.
        # rolling = sliding_window_view(self.Closeprice, (int(self.no_of_days), no_columns))
        rolling_windows = self.returns.rolling(window=int(self.windowSize))
        window_list = []
        for window_df in rolling_windows:
            tmp = window_df.dropna()
            if len(tmp.index) == int(self.windowSize):
                window_list.append(tmp)
        return window_list

    def rolling_div_return_list(self):
        rolling_windows = self.div_return.rolling(window=int(self.windowSize))
        window_list = []
        for window_df in rolling_windows:
            tmp = window_df.dropna()
            if len(tmp.index) == int(self.windowSize):
                window_list.append(tmp)
        return window_list

    def rolling_corr(self):
        rolling_windows = self.returns.rolling(window=int(self.windowSize))
        corr_matrix = rolling_windows.corr(pairwise=True)
        return corr_matrix
    
    def generate_correlation_matrix_from_store(self):
        if self.Closeprice.empty:
            raise ValueError("No close price data loaded.")

        # Filter valid tickers
        valid_tickers = [col for col in self.returns.columns if self.returns[col].notna().sum() > 0]
        df = self.returns[valid_tickers]

        # Sort by total correlation
        sorted_tickers = df.corr().sum().sort_values().index.tolist()
        corr_matrix = df[sorted_tickers].corr()

        return {
            "tickers": sorted_tickers,
            "matrix": corr_matrix.values.tolist()
        }