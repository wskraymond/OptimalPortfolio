import pandas as pd
import numpy as np
import pandas_datareader.data as web
import matplotlib.pyplot as plt
import scipy.optimize as solver
import datetime as dt
from functools import reduce
import seaborn as sns
import pandas_datareader as pdr

apiToken = 'b6aa06a239545aa707fc32cf7ffa17f3d828380f'
Closeprice = pd.DataFrame()
US_benchmark = 'VOO'
QQQ_benchmark = 'QQQ'
Gold = 'GLD'
BTC = 'IBIT'
Bond = 'TLT'
tickers = ['BRK-B', 'LIT', 'MSFT', 'AMZN', 'DBC', Gold, QQQ_benchmark, US_benchmark]
# tickers = [US_benchmark, QQQ_benchmark, Gold, BTC, Bond]

recvTickers = []
for i in tickers:
    try:
        print(i)
        tmp = pdr.get_data_tiingo(symbols=i, start='1/1/2024', end=dt.date.today(), retry_count=5, api_key=apiToken)
        tmp.reset_index('symbol', inplace=True, drop=True)
        Closeprice[i] = tmp['adjClose']
        recvTickers.append(i)
    except:
        print("symbol=", i, " cannot be resolved")

# calculate the log return
##returns is a dataframe class
returns = np.log(Closeprice / Closeprice.shift(1))

df = pd.DataFrame()
equity_columns = []

# Get symbol history
for symbol in recvTickers:
    try:
        symbol_df = returns[symbol]
        df = pd.concat([df, symbol_df], axis=1)
        equity_columns.append(symbol)
    except:
        print('Exception with {}'.format(symbol))

df.columns = equity_columns

# multi indexing
# https://pandas.pydata.org/docs/user_guide/advanced.html#using-slicers

# Get correlation and sort by sum
# sum_corr = df.corr().sum().sort_values(ascending=True).index.values
# print("sum_corr=", df.corr())
corr_matrix = df.rolling(window=20).corr(pairwise=True)
# print(corr_matrix.index.get_level_values(0).unique())
# print("corr_matrix=", corr_matrix.loc[(slice(None), 'VOO'), 'NVDA'])
# corr_matrix.to_csv(r'ui/output/corr.csv', index=True, header=True)

# plt.figure(figsize=(13, 8))
# cmap options: “RdYlGn_r”, “summer_r”, “Blues”, and “Greens”
# sns.heatmap(corr_matrix, annot=True, cmap="RdYlGn_r")
# stock_correlations = corr_matrix.xs(key=tickers, axis=0, level=1)

plt.figure(figsize=(10, 6))
i = corr_matrix.index.get_level_values(0).unique()
for a in corr_matrix.columns:
    for b in corr_matrix.columns:
        if a != b:
            s = corr_matrix.loc[(slice(None), a), b]
            plt.plot(i, s, label=f"{a}-{b}")

plt.xlabel('Date')
plt.ylabel('Correlation')
plt.title('Rolling Correlation Between Stocks')
plt.legend()
plt.grid(True)
plt.show()
