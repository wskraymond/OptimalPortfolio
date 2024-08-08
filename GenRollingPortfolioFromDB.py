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

from src.data.contract.MyContract import contractList
from src.data.store import Store
from datetime import datetime
import mplcursors


class Stats():
    def __init__(self, startdate, holdingPeriodYear):
        self.holdingPeriodYear = holdingPeriodYear
        self.no_of_days = 252 * self.holdingPeriodYear  # number of days for a quarter = 63
        self.fromDate = datetime.strptime(startdate, '%d/%m/%Y').date()
        self.Closeprice = pd.DataFrame()
        self.yc = None
        self.returns = None
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
        # https://pandas.pydata.org/docs/user_guide/timeseries.html
        self.Closeprice.index = pd.to_datetime(self.Closeprice.index)

    def pre_return(self):
        # calculate the log return
        # returns is a dataframe class
        self.returns = np.log(self.Closeprice / self.Closeprice.shift(1))
        return self.returns

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
        rolling_windows = self.returns.rolling(window=int(self.no_of_days))
        window_list = []
        for window_df in rolling_windows:
            tmp = window_df.dropna()
            if len(tmp.index) == int(self.no_of_days):
                window_list.append(tmp)
        return window_list

    def rolling_corr(self):
        rolling_windows = self.returns.rolling(window=int(self.no_of_days))
        corr_matrix = rolling_windows.corr(pairwise=True)
        return corr_matrix


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
            'margin_rate': self.single_period_margin_rate
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
    parser = ArgumentParser(
        prog='PorfolioOptimizer',
        description='PorfolioOptimizer')
    parser.add_argument('--holdingPeriodYear', default='0.25', type=float)
    parser.add_argument(
        '--startdate',
        required=True,
        help="'01/05/2015', '%d/%m/%Y'"
    )

    parser.add_argument(
        '--cmd',
        required=True,
        help="'o for optimal', 'o_avg for rolling avg of optimal', 'c 'orr for rolling correlation', 'ewm_corr_avg for avg of rolling correlation in heap map', 'beta_avg' ,std_avg' "
    )

    args = parser.parse_args()
    print("holdingPeriodYear=", args.holdingPeriodYear, "startdate=", args.startdate, "cmd=", args.cmd)

    stats = Stats(args.startdate, args.holdingPeriodYear)
    stats.loadYC()
    stats.loadDailyPrice()
    stats.pre_return()

    if args.cmd == 'o':
        rolling_return = stats.rolling_return_list()


        def rolling_optimize(ret):
            alloc = Allocation(stats, ret)
            alloc.preload()
            alloc.optimize()
            return alloc


        rolling_alloc = [rolling_optimize(ret.dropna()) for ret in rolling_return if not ret.empty]
        print(len(rolling_alloc))
        ratio_m = pd.DataFrame([alloc.get_result() for alloc in rolling_alloc],
                               index=[alloc.endDate for alloc in rolling_alloc])
        alloc_m = pd.DataFrame([alloc.get_allocation() for alloc in rolling_alloc],
                               index=[alloc.endDate for alloc in rolling_alloc])

        plt.figure(1)
        ratio_m.plot()
        plt.figure(2)
        alloc_m.plot()

        plt.show()
    elif args.cmd == 'o_avg':
        rolling_return = stats.rolling_return_list()


        def rolling_optimize(ret):
            alloc = Allocation(stats, ret)
            alloc.preload()
            alloc.optimize()
            return alloc


        rolling_alloc = [rolling_optimize(ret.dropna()) for ret in rolling_return if not ret.empty]
        print(len(rolling_alloc))
        ratio_m = pd.DataFrame([alloc.get_result() for alloc in rolling_alloc],
                               index=[alloc.endDate for alloc in rolling_alloc])
        alloc_m = pd.DataFrame([alloc.get_allocation() for alloc in rolling_alloc],
                               index=[alloc.endDate for alloc in rolling_alloc])

        alloc_mean = alloc_m.ewm(halflife=str(int(stats.no_of_days) / 2) + " days",
                                 times=alloc_m.index.get_level_values(0)).mean()
        ratio_mean = ratio_m.ewm(halflife=str(int(stats.no_of_days) / 2) + " days",
                                 times=ratio_m.index.get_level_values(0)).mean()

        plt.figure(1)
        ratio_mean.plot()
        plt.figure(2)
        alloc_mean.plot()

        plt.show()
    elif args.cmd == 'corr':
        corr_matrix = stats.rolling_corr()
        plt.figure(figsize=(10, 6))
        for a in corr_matrix.columns:
            for b in corr_matrix.columns:
                if a != b:
                    print(a, b)
                    y = corr_matrix.loc[(slice(None), a), b].dropna()
                    x = y.index.get_level_values(0).unique()
                    plt.plot(x, y, label=f"{a}-{b}")


        def show_annotation(sel):
            label = sel.artist.get_label()
            sel.annotation.set_text(f"{label}")


        mplcursors.cursor(hover=True).connect("add", show_annotation)

        plt.xlabel('Date')
        plt.ylabel('Correlation')
        plt.title('Rolling Correlation Between Stocks')
        plt.legend()
        plt.grid(True)
        plt.show()
    elif args.cmd == 'corr_3d':
        corr_matrix = stats.rolling_corr()
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        my_dict = {value: index for index, value in enumerate(corr_matrix.columns)}
        for a in corr_matrix.columns:
            for b in corr_matrix.columns:
                if a != b:
                    print(a, b)
                    s = corr_matrix.loc[(slice(None), a), b].dropna()
                    y = s.to_numpy()
                    i = s.index.get_level_values(0).unique().astype(int).to_numpy()
                    z = np.full_like(s, my_dict[a])
                    # print(type(i[0]), type(y), type(z))
                    # print(len(i), len(y), len(z))
                    ax.plot(z, i, y, label=f"{my_dict[a]}-{a}-{b}")
        ax.set_xlabel('stock')
        ax.set_ylabel('date')
        ax.set_zlabel('corr')
        ax.set_title('3D Rolling Correlation Between Stocks')
        ax.legend()
        plt.show()
    elif args.cmd == 'ewm_corr_avg':
        ret = stats.returns
        # https://pandas.pydata.org/docs/reference/api/pandas.core.window.ewm.ExponentialMovingWindow.corr.html#pandas.core.window.ewm.ExponentialMovingWindow.corr
        # corr = ret.ewm(halflife=str(int(stats.no_of_days)/2) + " days", times=ret.index.get_level_values(0)).corr()
        # Span corresponds to what is commonly called an “N-day EW moving average”.
        corr = ret.ewm(span=int(stats.no_of_days)).corr()
        # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.mean.html
        corr_matrix = corr.groupby(level=1).mean()
        # print(corr_matrix)
        # corr_matrix.to_csv(r'ui/output/corr.csv', index=True, header=True)

        plt.figure(2, figsize=(13, 8))
        # cmap options: “RdYlGn_r”, “summer_r”, “Blues”, and “Greens”
        sns.heatmap(corr_matrix, annot=True, cmap="RdYlGn_r")

        plt.title("Mean of Exponential Weighted Moving Correlation")
        plt.show()
    elif args.cmd == 'beta':
        betas = {}
        US_benchmark = 'SPY'
        HK_benchmark = '2800.HK'
        CN_benchmark = '159919.SZ'
        benchmarks = {US_benchmark}
        from scipy import stats as ss

        for i in stats.recvTickers:
            betas[i] = {}
            for j in benchmarks:
                slope, intercept, r, p, std_err = ss.linregress(np.nan_to_num(stats.returns[j].values),
                                                                np.nan_to_num(stats.returns[i].values))
                betas[i][j] = slope

        betas = pd.DataFrame(betas).transpose()
        print("betas=", betas)

    elif args.cmd == 'beta_avg':
        US_benchmark = 'SPY'
        # HK_benchmark = '2800.HK'
        # CN_benchmark = '159919.SZ'
        from scipy import stats as ss

        rolling_return = stats.rolling_return_list()


        def rolling_beta(ret):
            betas = {}
            for i in stats.recvTickers:
                betas[i] = {}
                slope, intercept, r, p, std_err = ss.linregress(np.nan_to_num(ret[US_benchmark].values),
                                                                np.nan_to_num(ret[i].values))
                betas[i] = slope

            startDate = ret.iloc[0].name
            endDate = ret.iloc[-1].name
            # print("betas=", betas, startDate, endDate)
            return startDate, endDate, betas


        rolling_b = [rolling_beta(ret.dropna()) for ret in rolling_return if not ret.empty]
        print(len(rolling_b))
        betas_m = pd.DataFrame([betas for startDate, endDate, betas in rolling_b],
                               index=[endDate for startDate, endDate, betas in rolling_b])

        rolling_avg = betas_m.ewm(halflife=str(int(stats.no_of_days) / 2) + " days",
                                  times=betas_m.index.get_level_values(0)).mean()

        plt.figure(1)
        rolling_avg.plot()

        plt.show()
        # betas.to_csv(r'ui/output/beta.csv', index=True, header=True)
    elif args.cmd == 'var':
        var = stats.returns.dropna().rolling(window=int(stats.no_of_days)).var()
        plt.figure(0)
        var.plot()
        plt.show()
    elif args.cmd == 'ewm_var':
        var = stats.returns.ewm(span=int(stats.no_of_days)).var()
        plt.figure(0)
        var.plot()
        plt.show()
    elif args.cmd == 'std':
        def roll_std(ret):
            mean_1 = np.exp(ret.mean() * stats.no_of_days)
            log_var = ret.var(skipna=True) * stats.no_of_days
            diff = np.exp(-1 * np.sqrt(log_var))
            std = np.subtract(diff * mean_1, mean_1)

            startDate = ret.iloc[0].name
            endDate = ret.iloc[-1].name
            return startDate, endDate, std * -100


        rolling_return = stats.rolling_return_list()
        rolling_std = [roll_std(ret.dropna()) for ret in rolling_return if not ret.empty]
        print(len(rolling_std))
        # print(rolling_std)
        std_m = pd.DataFrame([std for startDate, endDate, std in rolling_std],
                               index=[endDate for startDate, endDate, std in rolling_std])
        # print(ratio_m)
        std_m.plot()
        plt.show()

    elif args.cmd == 'std_avg':
        def roll_std(ret):
            mean_1 = np.exp(ret.mean() * stats.no_of_days)
            log_var = ret.var(skipna=True) * stats.no_of_days
            diff = np.exp(-1 * np.sqrt(log_var))
            std = np.subtract(diff * mean_1, mean_1)

            startDate = ret.iloc[0].name
            endDate = ret.iloc[-1].name
            return startDate, endDate, std * -100


        rolling_return = stats.rolling_return_list()
        rolling_std = [roll_std(ret.dropna()) for ret in rolling_return if not ret.empty]
        print(len(rolling_std))
        # print(rolling_std)
        std_m = pd.DataFrame([std for startDate, endDate, std in rolling_std],
                             index=[endDate for startDate, endDate, std in rolling_std])
        # print(ratio_m)
        std_avg = std_m.ewm(halflife=str(int(stats.no_of_days) / 2) + " days",
                   times=std_m.index.get_level_values(0)).mean()
        std_avg.plot()
        plt.show()