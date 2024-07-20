import pandas as pd
import numpy as np
import pandas_datareader as pdr
import matplotlib.pyplot as plt
import datetime as dt
from scipy.optimize import minimize
from argparse import ArgumentParser
import math
from pandas_datareader.data import DataReader as dr

parser = ArgumentParser(
    prog='PorfolioOptimizer',
    description='PorfolioOptimizer')
parser.add_argument('--holdingPeriodYear', default='0.25', type=float)
parser.add_argument(
    '--startdate',
    required=True,
    help="e.g 'JAN-01-2010', '1/1/10', 'Jan, 1, 1980'"
)

args = parser.parse_args()
print("holdingPeriodYear=", args.holdingPeriodYear, "startdate=",args.startdate)
holdingPeriodYear = args.holdingPeriodYear

syms = ['DGS30', 'DGS20', 'DGS10', 'DGS5', 'DGS2', 'DGS1', 'DGS1MO', 'DGS3MO']
yc = dr(syms, 'fred', '1/1/2024', dt.date.today())  # could specify start date with start param here
names = dict(zip(syms, ['30yr', '20yr', '10yr', '5yr', '2yr', '1yr', '1m', '3m']))
yc = yc.rename(columns=names)
yc = yc[['1m', '3m', '1yr', '2yr', '5yr', '10yr', '20yr', '30yr']]

no_of_days = 252 * holdingPeriodYear  # number of days for a quarter = 63

if holdingPeriodYear == 0.25:
    single_period_margin_rate = yc.iloc[-1]['3m'] / 100 / 4
elif holdingPeriodYear == 1:
    single_period_margin_rate = yc.iloc[-1]['1yr'] / 100
elif holdingPeriodYear == 2:
    single_period_margin_rate = math.pow(1 + yc.iloc[-1]['2yr'] / 100, 2) - 1
elif holdingPeriodYear == 5:
    single_period_margin_rate = math.pow(1 + yc.iloc[-1]['5yr'] / 100, 5) - 1
elif holdingPeriodYear == 10:
    single_period_margin_rate = math.pow(1 + yc.iloc[-1]['10yr'] / 100, 10) - 1
else:
    raise Exception("unsupported holding period")

print("single_period_margin_rate=", single_period_margin_rate)

Closeprice = pd.DataFrame()
US_benchmark = 'VOO'
QQQ_benchmark = 'QQQ'
TW_benchmark = 'EWT'
JP_benchmark = '1329.T'
HK_benchmark = '2800.HK'
CN_benchmark = '159919.SZ'
Gold = 'IAU'
BTC = 'IBIT'

# DJ Index
# table=pd.read_html('https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average')
# dj_df = table[1]
# tickers = set(dj_df['Symbol'].to_list())
# benchmarks = {US_benchmark}
# tickers = tickers.union(benchmarks)
# tickers = list(tickers)

# S&P 500 stock
sp_table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
sp_df = sp_table[0]
tickers = set(sp_df['Symbol'].to_list())
benchmarks = {US_benchmark, QQQ_benchmark, JP_benchmark,TW_benchmark, HK_benchmark, CN_benchmark, Gold, BTC}
tickers = tickers.union(benchmarks)
tickers = list(tickers)

# Nikkei 225 stock
# nk_df=pd.read_csv("csv/nikkei_225_list.csv")
# stockCode = filter(lambda str: str.isnumeric(), nk_df['Symbol'].to_list())
# tickers = set([s + '.T' for s in stockCode])
# benchmarks = {JP_benchmark}
# tickers = tickers.union(benchmarks)
# tickers = list(tickers)


# use pandas_datareader to get the close price data from tiingo finance giving the stock tickets and date
apiToken = 'b6aa06a239545aa707fc32cf7ffa17f3d828380f'
recvTickers = []
for i in tickers:
    try:
        print(i)
        # representations (e.g., 'JAN-01-2010', '1/1/10', 'Jan, 1, 1980')
        tmp = pdr.get_data_tiingo(symbols=i, start=args.startdate, end=dt.date.today(), retry_count=5, api_key=apiToken)
        tmp.reset_index('symbol', inplace=True, drop=True)
        Closeprice[i] = tmp['adjClose']
        recvTickers.append(i)
    except:
        print("symbol=", i, " cannot be resolved")

# calculate the log return
# returns is a dataframe class
returns = np.log(Closeprice / Closeprice.shift(1))

mean_1 = np.exp(returns.mean() * no_of_days)
log_var = returns.var(skipna=True) * no_of_days
diff = np.exp(-1 * np.sqrt(log_var))
std = np.subtract(diff * mean_1, mean_1)
var = pd.DataFrame()
for i in range(0, std.size):
    scalar = std[i]
    ds = std * scalar
    var[recvTickers[i]] = ds

corr = returns.corr()
cov = corr * var
mean = np.subtract(mean_1, 1)


def get_ret_vol_sr(weights):
    weights = np.array(weights)
    ret = np.sum(mean * weights)
    vol = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))
    sr = (ret - single_period_margin_rate) / vol
    return np.array([ret, vol, sr])


def neg_sharpe(weights):
    # the number 2 is the sharpe ratio index from the get_ret_vol_sr
    return get_ret_vol_sr(weights)[2] * -1


def check_sum(weights):
    # return 0 if sum of the weights is 1
    return np.sum(weights) - 1


# Our initial guess will be 25% for each stock (or 0.25), and the bounds will be a tuple (0,1) for each stock,
print("The number of stocks retrieved=", len(recvTickers))
cons = ({'type': 'eq', 'fun': check_sum})
bounds = [[0] * 2] * len(recvTickers)
bounds[0][1] = 1
# print(bounds)
equal_size = 1 / len(recvTickers)
print("equal_size=", equal_size)
init_guess = [equal_size] * len(recvTickers)
print("init_guess=", init_guess)

opt_result = minimize(neg_sharpe, init_guess, method='SLSQP', bounds=bounds, constraints=cons)
print(opt_result)

total = sum(opt_result.x)
print("total", total)
df = {}

j = 0
for i in recvTickers:
    df[i] = opt_result.x[j]
    j += 1

df = pd.DataFrame(df, index=[0]).transpose()
print(df)
df.to_csv(r'ui/output/optimal.csv', index=True, header=True)

# We want the key x from the dictionary, which is an array with the weights of the portfolio that has the maximum Sharpe ratio.
# If we use our function get_ret_vol_sr we get the return, volatility, and sharpe ratio:
sr_data = get_ret_vol_sr(opt_result.x)
ret_percent = sr_data[0]
vol_percent = sr_data[1]
sr_ratio = sr_data[2]

print("ret_percent=", ret_percent, "vol_percent=", vol_percent, "sr_ratio=", sr_ratio)

fig, ax = plt.subplots(figsize=(6, 3), subplot_kw=dict(aspect="equal"))
data = df[0].values
wedges, texts = ax.pie(data, wedgeprops=dict(width=0.5), startangle=-40)

bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=0.72)
kw = dict(arrowprops=dict(arrowstyle="-"),
          bbox=bbox_props, zorder=0, va="center")

for i, p in enumerate(wedges):
    ang = (p.theta2 - p.theta1) / 2. + p.theta1
    y = np.sin(np.deg2rad(ang))
    x = np.cos(np.deg2rad(ang))
    horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
    connectionstyle = "angle,angleA=0,angleB={}".format(ang)
    kw["arrowprops"].update({"connectionstyle": connectionstyle})
    ax.annotate("{:.2%} {}".format(data[i], df[0].index[i]), xy=(x, y), xytext=(1.35 * np.sign(x), 1.4 * y),
                horizontalalignment=horizontalalignment, **kw)

ax.set_title("Optimal Portfolio")

plt.show()
