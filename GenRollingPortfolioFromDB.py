import pandas as pd
import numpy as np
import pandas_datareader as pdr
import matplotlib.pyplot as plt
import datetime as dt

from pandas.core.window import Window
from scipy.optimize import minimize
from argparse import ArgumentParser
import math
from pandas_datareader.data import DataReader as dr
import traceback

from src.data.contract.MyContract import contractList
from src.data.store import Store
from datetime import datetime
from numpy.lib.stride_tricks import sliding_window_view


class Stats():
    def __init__(self):
        parser = ArgumentParser(
            prog='PorfolioOptimizer',
            description='PorfolioOptimizer')
        parser.add_argument('--holdingPeriodYear', default='0.25', type=float)
        parser.add_argument(
            '--startdate',
            required=True,
            help="'01/05/2015', '%d/%m/%Y'"
        )

        args = parser.parse_args()
        print("holdingPeriodYear=", args.holdingPeriodYear, "startdate=", args.startdate)

        self.holdingPeriodYear = args.holdingPeriodYear
        self.no_of_days = 252 * self.holdingPeriodYear  # number of days for a quarter = 63
        self.fromDate = datetime.strptime(args.startdate, '%d/%m/%Y').date()
        self.Closeprice = pd.DataFrame()
        self.yc = None
        self.recvTickers = []

    def loadYC(self):
        syms = ['DGS30', 'DGS20', 'DGS10', 'DGS5', 'DGS2', 'DGS1', 'DGS1MO', 'DGS3MO']
        yc = dr(syms, 'fred', self.fromDate, dt.date.today())  # could specify start date with start param here
        names = dict(zip(syms, ['30yr', '20yr', '10yr', '5yr', '2yr', '1yr', '1m', '3m']))
        yc = yc.rename(columns=names)
        yc = yc[['1m', '3m', '1yr', '2yr', '5yr', '10yr', '20yr', '30yr']]
        yc.index = pd.to_datetime(yc.index)
        # print(yc)
        self.yc = yc

    def loadDailyPrice(self):
        store = Store(hosts=['127.0.0.1'], keyspace='store')
        for i in contractList:
            try:
                print(i.symbol)
                rows = store.select_daily_price_in_pd_by_range(ticker=i.symbol,
                                                               fromDate=self.fromDate,
                                                               toDate=dt.date.today())
                self.Closeprice[i.symbol] = rows['close']
                self.recvTickers.append(i.symbol)
            except Exception as error:
                print("An error occurred:", error)
                traceback.print_exc()
                print("symbol=", i.symbol, " cannot be resolved")

        self.Closeprice.index = pd.to_datetime(self.Closeprice.index)

    # window operation doc
    # https://pandas.pydata.org/docs/reference/window.html

    # rolling apply to specific function
    # https://pandas.pydata.org/docs/user_guide/window.html#rolling-apply

    # https://pandas.pydata.org/docs/user_guide/window.html#computing-rolling-pairwise-covariances-and-correlations
    # rolling window operation

    def rolling_return(self):
        # Also known as rolling or moving window,
        # the window slides across all dimensions of the array and extracts subsets of the array at all window positions.
        # rolling = sliding_window_view(self.Closeprice, (int(self.no_of_days), no_columns))

        # calculate the log return
        # returns is a dataframe class
        returns = np.log(self.Closeprice / self.Closeprice.shift(1))
        rolling_windows = returns.rolling(window=int(self.no_of_days))
        window_list = []
        for window_df in rolling_windows:
            tmp = window_df.dropna()
            if len(tmp.index) == int(self.no_of_days):
                window_list.append(tmp)
        return window_list


class Allocation():
    def __init__(self, stat: Stats, returns):
        self.stat = stat
        self.corr = None
        self.cov = None
        self.mean = None
        self.df = {}
        self.sr_data = None

        self.returns = returns
        self.startDate = returns.iloc[0].name
        self.endDate = returns.iloc[-1].name
        self.single_period_margin_rate = self.load_margin_rate(self.startDate)

    def load_margin_rate(self, date):
        try:
            if self.stat.holdingPeriodYear == 0.25:
                single_period_margin_rate = self.stat.yc.loc[date]['3m'] / 100 / 4
            elif self.stat.holdingPeriodYear == 1:
                single_period_margin_rate = self.stat.yc.loc[date]['1yr'] / 100
            elif self.stat.holdingPeriodYear == 2:
                single_period_margin_rate = math.pow(1 + self.stat.yc.loc[date]['2yr'] / 100, 2) - 1
            elif self.stat.holdingPeriodYear == 5:
                single_period_margin_rate = math.pow(1 + self.stat.yc.loc[date]['5yr'] / 100, 5) - 1
            elif self.stat.holdingPeriodYear == 10:
                single_period_margin_rate = math.pow(1 + self.stat.yc.loc[date]['10yr'] / 100, 10) - 1
            else:
                raise Exception("unsupported holding period")
        except Exception as error:
            print("An error occurred:", error)
            traceback.print_exc()

        # print("single_period_margin_rate=", single_period_margin_rate)
        return single_period_margin_rate

    def preload(self):
        mean_1 = np.exp(self.returns.mean() * self.stat.no_of_days)
        log_var = self.returns.var(skipna=True) * self.stat.no_of_days
        diff = np.exp(-1 * np.sqrt(log_var))
        std = np.subtract(diff * mean_1, mean_1)
        var = pd.DataFrame()
        for i in range(0, std.size):
            scalar = std[i]
            ds = std * scalar
            var[self.stat.recvTickers[i]] = ds

        self.corr = self.returns.corr()
        self.cov = self.corr * var
        self.mean = np.subtract(mean_1, 1)

    def gen_ret_vol_sr_func(self):
        def get_ret_vol_sr(weights):
            weights = np.array(weights)
            ret = np.sum(self.mean * weights)
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
            'ret_percent': self.sr_data[0],
            'vol_percent': self.sr_data[1],
            'sr_ratio': self.sr_data[2],
            'margin_rate' : self.single_period_margin_rate
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


if __name__ == "__main__":
    stats = Stats()
    stats.loadYC()
    stats.loadDailyPrice()
    rolling_return = stats.rolling_return()

    def rolling_optimize(ret):
        alloc = Allocation(stats, ret)
        alloc.preload()
        alloc.optimize()
        return alloc

    rolling_alloc = [rolling_optimize(ret.dropna()) for ret in rolling_return if not ret.empty]
    print(len(rolling_alloc))
    ratio_ma = pd.DataFrame([alloc.get_result() for alloc in rolling_alloc],
                            index=[alloc.endDate for alloc in rolling_alloc])
    alloc_ma = pd.DataFrame([alloc.get_allocation() for alloc in rolling_alloc],
                            index=[alloc.endDate for alloc in rolling_alloc])

    plt.figure(1)
    ratio_ma.plot()
    plt.figure(2)
    alloc_ma.plot()

    plt.show()
