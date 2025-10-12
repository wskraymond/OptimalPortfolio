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

from src.data.contract.MyContract import contractList
from src.data.store import Store
from datetime import datetime
import mplcursors
import yfinance as yf
from yahooquery import Ticker
from ibapi.contract import Contract

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
        self.holdingPeriodYear = holdingPeriodYear
        self.no_of_days = 252 * self.holdingPeriodYear  # number of days for a quarter = 63
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
        self.windowSize = 252 * rollingYr
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


if __name__ == "__main__":
    parser = ArgumentParser(
        prog='PorfolioOptimizer',
        description='PorfolioOptimizer')
    parser.add_argument('--holdingPeriodYear', default='0.25', type=float)
    parser.add_argument('--rollingYr', default='5', type=float)
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

    parser.add_argument(
        '--divTaxRate',
        default=0.3,
        type=float,
        help="default 30%"
    )

    args = parser.parse_args()
    print("holdingPeriodYear=", args.holdingPeriodYear, "rollingYr=", args.rollingYr, "startdate=", args.startdate,
          "cmd=", args.cmd, "divTaxRate=",
          args.divTaxRate)

    stats = Stats(args.startdate, args.holdingPeriodYear, args.rollingYr, args.divTaxRate)
    stats.loadYC()
    stats.loadDailyPrice()
    stats.load_div_expense()
    stats.after_tax()
    stats.pre_return()
    stats.pre_div_return()
    stats.pre_log_expense()

    if args.cmd == 'div':
        print("log mean \n", stats.returns.mean())
        print("log mean std \n", stats.returns.std())
        print("div log ret mean \n", stats.div_return.mean())
        print("div log ret std \n", stats.div_return.std())
        print("expense \n", (np.exp(stats.log_expense) - 1) * 100)
        plt.figure(0)
        stats.returns.plot()
        plt.title("log return")
        plt.savefig('log_return.png')

        plt.figure(1)
        div = stats.div.groupby(stats.div.index.year).sum()
        div.plot()
        plt.title("tax adjusted div payment over year")
        plt.savefig('div_0.png')

        plt.figure(2)
        div_yield = (np.exp(stats.div_return.groupby(stats.div_return.index.year).sum()) - 1) * 100
        div_yield.plot()
        plt.title("tax adjusted div yield per year")
        plt.savefig('div_1.png')

        plt.figure(4)
        div_yield_over_time = (div / stats.Closeprice.loc[stats.Closeprice.first_valid_index()]) * 100
        for ticker in div_yield_over_time.columns:
            div_line = div_yield_over_time[ticker]
            close_price = stats.Closeprice.loc[stats.Closeprice.first_valid_index(), ticker]
            date = stats.Closeprice[ticker].first_valid_index().date()
            label = f"{ticker}@{close_price:.2f} on {date}"
            div_line.plot(label=label)

        plt.title("Tax-Adjusted Dividend Yield Over Years Since First Funding")
        plt.legend()
        plt.grid(True)
        plt.show()
        plt.savefig('div_2.png')
    elif args.cmd == 'o':
        rolling_return = stats.rolling_return_list()
        rolling_div_return = stats.rolling_div_return_list()


        def rolling_optimize(ret, div):
            alloc = Allocation(stats, ret, div)
            alloc.preload()
            alloc.optimize()
            return alloc


        rolling_alloc = [rolling_optimize(ret.dropna(), div.dropna()) for ret, div in
                         zip(rolling_return, rolling_div_return) if not ret.empty and not div.empty]
        ratio_m = pd.DataFrame([alloc.get_result() for alloc in rolling_alloc],
                               index=[alloc.endDate for alloc in rolling_alloc])
        alloc_m = pd.DataFrame([alloc.get_allocation() for alloc in rolling_alloc],
                               index=[alloc.endDate for alloc in rolling_alloc])

        plt.figure(1)
        ratio_m.plot()
        plt.title(f"Ratio - optimal portfolio with {int(stats.holdingPeriodYear)}Y HPR rolling over {int(stats.rollingYr)}Y window")
        plt.figure(2)
        alloc_m.plot()
        plt.title(f"Alloc - optimal portfolio with {int(stats.holdingPeriodYear)}Y HPR rolling over {int(stats.rollingYr)}Y window")

        plt.show()
        plt.savefig('o.png')
    elif args.cmd == 'o_avg':
        rolling_return = stats.rolling_return_list()
        rolling_div_return = stats.rolling_div_return_list()


        def rolling_optimize(ret, div):
            alloc = Allocation(stats, ret, div)
            alloc.preload()
            alloc.optimize()
            return alloc


        rolling_alloc = [rolling_optimize(ret.dropna(), div.dropna()) for ret, div in
                         zip(rolling_return, rolling_div_return) if not ret.empty and not div.empty]
        ratio_m = pd.DataFrame([alloc.get_result() for alloc in rolling_alloc],
                               index=[alloc.endDate for alloc in rolling_alloc])
        alloc_m = pd.DataFrame([alloc.get_allocation() for alloc in rolling_alloc],
                               index=[alloc.endDate for alloc in rolling_alloc])

        alloc_mean = alloc_m.ewm(halflife=str(int(stats.windowSize) / 2) + " days",
                                 times=alloc_m.index.get_level_values(0)).mean()
        ratio_mean = ratio_m.ewm(halflife=str(int(stats.windowSize) / 2) + " days",
                                 times=ratio_m.index.get_level_values(0)).mean()

        plt.figure(1)
        ratio_mean.plot()
        plt.title(f"Ratio - optimal portfolio with {int(stats.holdingPeriodYear)}Y HPR rolling over {int(stats.rollingYr)}Y EMA")
        plt.figure(2)
        alloc_mean.plot()
        plt.title(f"Alloc - optimal portfolio with {int(stats.holdingPeriodYear)}Y HPR rolling over {int(stats.rollingYr)}Y EMA")
        plt.grid(True)
        plt.show()
        plt.savefig('o_avg.png')
    elif args.cmd == 'corr':
        corr_matrix = stats.rolling_corr()
        plt.figure(figsize=(10, 6))
        for a in corr_matrix.columns:
            for b in corr_matrix.columns:
                if a != b:
                    print(a, b)
                    y = corr_matrix.loc[(slice(None), a), b].dropna()
                    x = y.index.get_level_values(0).unique().to_numpy()
                    y = y.to_numpy()
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
        plt.savefig('corr.png')
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
                    ax.plot(z, i, y, label=f"{my_dict[a]}-{a}-{b}")
        ax.set_xlabel('stock')
        ax.set_ylabel('date')
        ax.set_zlabel('corr')
        ax.set_title('3D Rolling Correlation Between Stocks')
        ax.legend()
        plt.show()
        plt.savefig('corr_3d.png')
    elif args.cmd == 'ewm_corr_avg':
        ret = stats.returns
        # https://pandas.pydata.org/docs/reference/api/pandas.core.window.ewm.ExponentialMovingWindow.corr.html#pandas.core.window.ewm.ExponentialMovingWindow.corr
        # corr = ret.ewm(halflife=str(int(stats.no_of_days)/2) + " days", times=ret.index.get_level_values(0)).corr()
        # Span corresponds to what is commonly called an “N-day EW moving average”.
        corr = ret.ewm(span=int(stats.windowSize)).corr()
        # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.mean.html
        corr_matrix = corr.groupby(level=1).mean()

        plt.figure(2, figsize=(13, 8))
        # cmap options: “RdYlGn_r”, “summer_r”, “Blues”, and “Greens”
        sns.heatmap(corr_matrix, annot=True, cmap="RdYlGn_r")

        plt.title("Mean of Exponential Weighted Moving Correlation")
        plt.show()
        plt.savefig('ewm_corr_avg.png')
    elif args.cmd == 'beta':
        betas = {}
        US_benchmark = 'SPY'
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

        rolling_avg = betas_m.ewm(halflife=str(int(stats.windowSize) / 2) + " days",
                                  times=betas_m.index.get_level_values(0)).mean()

        plt.figure(1)
        rolling_avg.plot()

        plt.show()
        plt.savefig('beta_avg.png')
    elif args.cmd == 'var':
        var = stats.returns.dropna().rolling(window=int(stats.windowSize)).var() * stats.no_of_days
        plt.figure(0)
        var.plot()
        plt.show()
        plt.savefig('var.png')
    elif args.cmd == 'ewm_var':
        var = stats.returns.ewm(span=int(stats.windowSize)).var() * stats.no_of_days
        plt.figure(0)
        var.plot()
        plt.show()
        plt.savefig('ewm_var.png')
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
        std_m = pd.DataFrame([std for startDate, endDate, std in rolling_std],
                             index=[endDate for startDate, endDate, std in rolling_std])
        std_m.plot()
        plt.show()
        plt.savefig('std.png')

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
        std_m = pd.DataFrame([std for startDate, endDate, std in rolling_std],
                             index=[endDate for startDate, endDate, std in rolling_std])
        std_avg = std_m.ewm(halflife=str(int(stats.windowSize) / 2) + " days",
                            times=std_m.index.get_level_values(0)).mean()
        std_avg.plot()
        plt.grid(True)
        plt.title(f"Rolling Risk in a {stats.holdingPeriodYear}-Y holding Period")
        plt.show()
        plt.savefig('std_avg.png')
