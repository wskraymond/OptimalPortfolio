import pandas as pd
import numpy as np
import pandas_datareader.data as web
import matplotlib.pyplot as plt
import scipy.optimize as solver
import datetime as dt
from functools import reduce
import seaborn as sns
from scipy import stats
from sklearn import linear_model
import math
import pandas_datareader as pdr

US_benchmark = 'SPY'
HK_benchmark = '2800.HK'
CN_benchmark = '159919.SZ'
margin_rate = 1
Closeprice = pd.DataFrame()
# tickers = {'BRK-B','LIT','ARKK','BIDU','DBC','REET','9988.HK', '0001.HK','2840.hk'}
tickers = {'BRK-B', 'LIT', 'MSFT', 'AMZN', 'DBC', 'TSLA', 'NVDA'}
# benchmarks = {US_benchmark, HK_benchmark, CN_benchmark}
benchmarks = {US_benchmark}

apiToken = 'b6aa06a239545aa707fc32cf7ffa17f3d828380f'
recvTickers = {}
for i in tickers.union(benchmarks):
    try:
        print(i)
        tmp = pdr.get_data_tiingo(symbols=i, start='1/1/2023', end=dt.date.today(), retry_count=5, api_key=apiToken)
        tmp.reset_index('symbol', inplace=True, drop=True)
        Closeprice[i] = tmp['adjClose']
        recvTickers.add(i)
    except:
        print("symbol=", i, " cannot be resolved")

# calculate the log return
##returns is a dataframe class
returns = np.log(Closeprice / Closeprice.shift(1))
# print(np.nan_to_num(returns[benchmark].values))

betas = {}
for i in recvTickers.union(benchmarks):
    betas[i] = {}
    for j in benchmarks:
        slope, intercept, r, p, std_err = stats.linregress(np.nan_to_num(returns[j].values),
                                                           np.nan_to_num(returns[i].values))
        betas[i][j] = slope

betas = pd.DataFrame(betas).transpose()
print("betas=", betas)

betas.to_csv(r'ui/output/beta.csv', index=True, header=True)

size = len(recvTickers) + len(benchmarks)

# Expected return
# normal value
# ret_arr = np.multiply(np.subtract(np.exp(returns.mean() * 252), 1), 100)
# lognormal
ret_arr = returns.mean()
ret_arr = pd.DataFrame(ret_arr)
print("ret_arr=", ret_arr)

ret_arr.to_csv(r'ui/output/log_daily_return.csv', index=True, header=True)

# Expected volatility
# percent : exp(-x) != exp(+x) ???
# normal value
# vol_arr = np.multiply(np.subtract(np.exp(np.sqrt(returns.var()*252)), 1), 100)
# log normal value
vol_arr = returns.var()
vol_arr = pd.DataFrame(vol_arr)
print("vol_arr=", vol_arr)

vol_arr.to_csv(r'ui/output/log_daily_var.csv', index=True, header=True)
