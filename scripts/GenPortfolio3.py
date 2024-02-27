import pandas as pd
import numpy as np
import pandas_datareader.data as web
import pandas_datareader as pdr
import matplotlib.pyplot as plt
import scipy.optimize as solver
import datetime as dt
from functools import reduce
import math
# from lib.loadTiingo import getLatestPriceFromTickers, getInfoFromTickers
import sys

# use pandas_datareader to get the close price data from Yahoo finance giving the stock tickets and date
from scipy.optimize import minimize

no_of_days = 63 #quaterly
single_period_margin_rate = 0.03

Closeprice = pd.DataFrame()
US_benchmark = 'SPY'
HK_benchmark = '2800.HK'
CN_benchmark = '159919.SZ'

#DJ Index
# table=pd.read_html('https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average')
# dj_df = table[1]  #.head(2)
# tickers = set(dj_df['Symbol'].to_list())
# benchmarks = {US_benchmark}
# tickers = tickers.union(benchmarks) #- set('APD') #filter 'APD'
# tickers = list(tickers)

#S&P 500 stock
sp_table=pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
sp_df = sp_table[0] #.head(2)   ###testing first 2 stocks
tickers = set(sp_df['Symbol'].to_list())
benchmarks = {US_benchmark}
tickers = tickers.union(benchmarks) #- set('APD') #filter 'APD'
tickers = list(tickers)

#plz use short list of data for testing
# tickers = ['BRK-B','LIT','MSFT','AMZN','DBC','TSLA', 'NVDA', US_benchmark]
# tickers = ['BRK-B','LIT','ARKK','DBC','REET', 'NVDA', 'MSFT','AMZN', 'TSLA', 'JPM', US_benchmark]


#use pandas_datareader to get the close price data from tiingo finance giving the stock tickets and date
apiToken = 'b6aa06a239545aa707fc32cf7ffa17f3d828380f'
recvTickers=[]
for i in tickers:
    try:
        print(i)
        tmp = pdr.get_data_tiingo(symbols=i,start='1/1/2023', end=dt.date.today(), retry_count=5, api_key=apiToken)
        tmp.reset_index('symbol', inplace=True, drop=True)
        Closeprice[i] = tmp['adjClose']
        recvTickers.append(i)
    except:
        print("symbol=",i," cannot be resolved")

# calculate the log return
##returns is a dataframe class
returns = np.log(Closeprice / Closeprice.shift(1))

mean_1 = np.exp(returns.mean() * no_of_days)
# print("mean_1")
# print(mean_1)
log_var = returns.var(skipna=True) * no_of_days
# print("log_var")
# print(log_var)
diff = np.exp(-1*np.sqrt(log_var))
std = np.subtract(diff*mean_1, mean_1)
# print("std")
# print(std)
var = pd.DataFrame()
for i in range(0, std.size):
    scalar = std[i]
    ds = std*scalar
    var[recvTickers[i]] = ds

# print("var")
# print(var)
corr = returns.corr()

# print("corr")
# print(corr)
cov = corr*var

# print("cov")
# print(cov)
mean = np.subtract(mean_1,1)

def get_ret_vol_sr(weights):
    weights = np.array(weights)
    # print("weights=", weights)
    ret = np.sum(mean * weights)
    # print("ret=",ret)
    vol = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))
    # print("vol=",vol)
    sr = (ret - single_period_margin_rate) / vol
    # print("sr=",sr)
    return np.array([ret, vol, sr])


def neg_sharpe(weights):
    # the number 2 is the sharpe ratio index from the get_ret_vol_sr
    return get_ret_vol_sr(weights)[2] * -1


def check_sum(weights):
    # return 0 if sum of the weights is 1
    return np.sum(weights) - 1


# Moving on, we will need to create a variable to include our constraints like the check_sum.
# We’ll also define an initial guess and specific bounds, to help the minimization be faster and more efficient.
# Our initial guess will be 25% for each stock (or 0.25), and the bounds will be a tuple (0,1) for each stock,
# since the weight can range from 0 to 1.

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

#https://matplotlib.org/stable/gallery/pie_and_polar_charts/pie_and_donut_labels.html
# fig, ax = plt.subplots(figsize=(6, 3), subplot_kw=dict(aspect="equal"))
#
# data = df[0].values
# labels = df[0].index
#
# wedges, texts, autotexts = ax.pie(data, autopct='%1.1f%%',
#                                   textprops=dict(color="w"))
#
# ax.legend(wedges, labels,
#           title="Ingredients",
#           loc="center left",
#           bbox_to_anchor=(1, 0, 0.5, 1))
#
# plt.setp(autotexts, size=8, weight="bold")
#
# plt.show()


fig, ax = plt.subplots(figsize=(6, 3), subplot_kw=dict(aspect="equal"))

data = df[0].values

wedges, texts = ax.pie(data, wedgeprops=dict(width=0.5), startangle=-40)

bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=0.72)
kw = dict(arrowprops=dict(arrowstyle="-"),
          bbox=bbox_props, zorder=0, va="center")

for i, p in enumerate(wedges):
    ang = (p.theta2 - p.theta1)/2. + p.theta1
    y = np.sin(np.deg2rad(ang))
    x = np.cos(np.deg2rad(ang))
    horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
    connectionstyle = "angle,angleA=0,angleB={}".format(ang)
    kw["arrowprops"].update({"connectionstyle": connectionstyle})
    ax.annotate("{:.2%} {}".format(data[i],df[0].index[i]), xy=(x, y), xytext=(1.35*np.sign(x), 1.4*y),
                horizontalalignment=horizontalalignment, **kw)

ax.set_title("Optimal Portfolio")

plt.show()