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

#S&P 500 stock
# sp_table=pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
# sp_df = sp_table[0].head(2)   ###testing first 2 stocks
# tickers = set(sp_df['Symbol'].to_list())
# benchmarks = {US_benchmark}
# tickers = tickers.union(benchmarks) #- set('APD') #filter 'APD'

#plz use short list of data for testing
# tickers = ['BRK-B','LIT','ARKK','BIDU','DBC','REET','9988.HK', '0001.HK','2840.hk', US_benchmark , HK_benchmark,CN_benchmark]
tickers = ['BRK-B','LIT','ARKK','DBC','REET', 'NVDA', 'MSFT','AMZN', 'TSLA', 'JPM', US_benchmark]

#use pandas_datareader to get the close price data from tiingo finance giving the stock tickets and date
apiToken = 'b6aa06a239545aa707fc32cf7ffa17f3d828380f'
for i in tickers:
    print(i)
    tmp = pdr.get_data_tiingo(symbols=i,start='1/1/2019', end=dt.date.today(), retry_count=5, api_key=apiToken)
    tmp.reset_index('symbol', inplace=True, drop=True)
    Closeprice[i] = tmp['adjClose']

# calculate the log return
##returns is a dataframe class
returns = np.log(Closeprice / Closeprice.shift(1))


def get_ret_vol_sr(weights):
    weights = np.array(weights)
    mean = np.exp(returns.mean() * no_of_days)
    # print(mean)
    diff = np.exp(-1*np.sqrt(returns.cov() * no_of_days))
    std = np.subtract(np.multiply(mean, diff), mean)
    cov = np.power(std, 2)
    # print(cov)

    mean = np.subtract(mean,1)

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


# Moving on, we will need to create a variable to include our constraints like the check_sum.
# We’ll also define an initial guess and specific bounds, to help the minimization be faster and more efficient.
# Our initial guess will be 25% for each stock (or 0.25), and the bounds will be a tuple (0,1) for each stock,
# since the weight can range from 0 to 1.

cons = ({'type': 'eq', 'fun': check_sum})
bounds = [[0] * 2] * len(tickers)
bounds[0][1] = 1
print(bounds)
init_guess = [0.25] * len(tickers)
print(init_guess)

opt_result = minimize(neg_sharpe, init_guess, method='SLSQP', bounds=bounds, constraints=cons)
print(opt_result)

total = sum(opt_result.x)
print("total", total)
df = {}

j = 0
for i in tickers:
    df[i] = opt_result.x[j]
    j += 1

df = pd.DataFrame(df, index=[0]).transpose()
print(df)
df.to_csv(r'optimal.csv', index=True, header=True)

# We want the key x from the dictionary, which is an array with the weights of the portfolio that has the maximum Sharpe ratio.
# If we use our function get_ret_vol_sr we get the return, volatility, and sharpe ratio:
sr_data = get_ret_vol_sr(opt_result.x)
ret_percent = math.exp(sr_data[0]) - 1
vol_percent = math.exp(sr_data[1])
sr_ratio = sr_data[2]

print("ret_percent", ret_percent, "vol_percent", vol_percent, "sr_ratio", sr_ratio)
