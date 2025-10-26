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
from analytics.Stats import Stats
from datetime import datetime
import mplcursors
import yfinance as yf
from yahooquery import Ticker
from ibapi.contract import Contract
from scipy import stats as ss

store_host = 'host.docker.internal'


class Allocation():
    def __init__(self, stat: Stats, returns, div_return):
        self.stat = stat
        self.corr = None
        self.cov = None
        self.hpr = None
        self.df = {}
        self.sr_data = None

        self.returns = returns
        self.div_return = div_return
        self.startDate = returns.iloc[0].name
        self.endDate = returns.iloc[-1].name
        self.single_period_margin_rate, self.single_period_expense_series = self.load_holding_period_data(
            self.startDate)

    def load_holding_period_data(self, date):
        single_period_expense_series = self.stat.log_expense
        try:
            if self.stat.rollingYr < self.stat.holdingPeriodYear:
                raise Exception(f"{self.stat.rollingYr} < {self.stat.holdingPeriodYear}")
            if self.stat.rollingYr == 0.25:
                single_period_margin_rate = self.stat.yc.loc[date]['3m'] * self.stat.holdingPeriodYear / 100
            elif self.stat.rollingYr == 1:
                single_period_margin_rate = math.pow(1 + self.stat.yc.loc[date]['1yr'] / 100,
                                                     self.stat.holdingPeriodYear) - 1
            elif self.stat.rollingYr == 2:
                single_period_margin_rate = math.pow(1 + self.stat.yc.loc[date]['2yr'] / 100,
                                                     self.stat.holdingPeriodYear) - 1
            elif self.stat.rollingYr == 5:
                single_period_margin_rate = math.pow(1 + self.stat.yc.loc[date]['5yr'] / 100,
                                                     self.stat.holdingPeriodYear) - 1
            elif self.stat.rollingYr == 10:
                single_period_margin_rate = math.pow(1 + self.stat.yc.loc[date]['10yr'] / 100,
                                                     self.stat.holdingPeriodYear) - 1
            else:
                raise Exception("unsupported rollingYr")
        except Exception as error:
            print("An error occurred:", error)
            traceback.print_exc()

        single_period_expense_series = np.multiply(single_period_expense_series, self.stat.holdingPeriodYear)
        # print("single_period_margin_rate=", single_period_margin_rate)
        # print("single_period_expense_series=", single_period_expense_series)
        return single_period_margin_rate, single_period_expense_series

    def preload(self):
        HPR_1 = np.exp(self.returns.mean() * self.stat.no_of_days)
        # total return => captial gain + tax adjusted dividend gain - etf expense
        # total_HPR_1 = np.exp(self.returns.sum(axis=0) + self.div_return.sum(axis=0) + self.single_period_expense_series)
        # if window size == self.stat.no_of_days, then actually we don't need to calculate mean and multiply
        total_HPR_1 = np.exp(
            (self.returns.mean() + self.div_return.mean()) * self.stat.no_of_days + self.single_period_expense_series)
        log_var = self.returns.var(skipna=True) * self.stat.no_of_days
        diff = np.exp(-1 * np.sqrt(log_var))
        std = np.subtract(diff * HPR_1, HPR_1)
        var = pd.DataFrame()
        for i in range(0, std.size):
            scalar = std[i]
            ds = std * scalar
            var[self.stat.recvTickers[i]] = ds

        self.corr = self.returns.corr()
        self.cov = self.corr * var
        self.hpr = np.subtract(total_HPR_1, 1)

    def gen_ret_vol_sr_func(self):
        def get_ret_vol_sr(weights):
            weights = np.array(weights)
            ret = np.sum(self.hpr * weights)
            vol = np.sqrt(np.dot(weights.T, np.dot(self.cov, weights)))
            sr = (ret - self.single_period_margin_rate) / vol
            return np.array([ret, vol, sr])

        return get_ret_vol_sr

    def gen_neg_sharpe_func(self):
        def neg_sharpe(weights):
            # the number 2 is the sharpe ratio index from the get_ret_vol_sr
            return self.gen_ret_vol_sr_func()(weights)[2] * -1

        return neg_sharpe

    def gen_check_sum_func(self):
        def check_sum(weights):
            # return 0 if sum of the weights is 1
            return np.sum(weights) - 1

        return check_sum

    def to_csv(self):
        print("generate csv file")
        self.df.to_csv(r'ui/output/optimal.csv', index=True, header=True)

    def optimize(self):
        # Our initial guess will be 25% for each stock (or 0.25), and the bounds will be a tuple (0,1) for each stock,
        # print("The number of stocks retrieved=", len(self.stat.recvTickers))
        cons = ({'type': 'eq', 'fun': self.gen_check_sum_func()})
        bounds = [[0] * 2] * len(self.stat.recvTickers)
        bounds[0][1] = 1
        equal_size = 1 / len(self.stat.recvTickers)
        init_guess = [equal_size] * len(self.stat.recvTickers)

        opt_result = minimize(self.gen_neg_sharpe_func(), init_guess, method='SLSQP', bounds=bounds, constraints=cons)
        self.df = {}
        j = 0
        for i in self.stat.recvTickers:
            self.df[i] = opt_result.x[j]
            j += 1

        self.df = pd.DataFrame(self.df, index=[0]).transpose()
        # print(self.df)

        # We want the key x from the dictionary, which is an array with the weights of the portfolio that has the maximum Sharpe ratio.
        # If we use our function get_ret_vol_sr we get the return, volatility, and sharpe ratio:
        self.sr_data = self.gen_ret_vol_sr_func()(opt_result.x)

    def get_result(self):
        return {
            'ret_percent': self.sr_data[0] * 100,
            'vol_percent': self.sr_data[1] * 100,
            'sr_ratio': self.sr_data[2] * 100,
            'margin_rate': self.single_period_margin_rate * 100
        }

    def get_allocation(self):
        return self.df.to_dict()[0]

    def to_dict(self):
        r = self.get_result()
        a = self.get_allocation()
        dict = {}
        dict.update(r)
        dict.update(a)
        return dict
    
    def calc_period_alpha_capm(self,
                           betas: pd.DataFrame,
                           benchmark: str = 'VOO') -> pd.Series:
        """
        Compute CAPM alpha over the holding period (no annualization):
        α_period = R_i,period − [ r_f,period + β_i * (R_m,period − r_f,period) ]

        Uses:
        - self.hpr: 1‐period total return for each ticker (e.g. 3-month or 1-year)
        - self.single_period_margin_rate: matching risk‐free return over that period
        - betas: DataFrame indexed by ticker, with column=benchmark holding β_i
        """
        tickers = self.stat.recvTickers

        # 1. Realized period return (array of holding‐period returns)
        R_period = pd.Series(self.hpr, index=tickers)
        print("R_period=", R_period)

        # 2. Risk‐free return over the same holding period
        rf_period = self.single_period_margin_rate

        # 3. Market’s realized return over the holding period
        Rm_period = R_period[benchmark]

        # 4. CAPM‐expected period return per ticker
        beta_series = betas[benchmark]
        #print("rf_period=", rf_period, " Rm_period=", Rm_period, " beta_series=", beta_series)
        E_period = rf_period + beta_series * (Rm_period - rf_period)

        # 5. Period CAPM alpha
        alpha_period = R_period - E_period

        return alpha_period