import pandas as pd
import numpy as np
import pandas_datareader.data as web
import matplotlib.pyplot as plt
import scipy.optimize as solver
import datetime as dt
from functools import reduce
import seaborn as sns

Closeprice = pd.DataFrame()
US_benchmark = 'SPY'
HK_benchmark = '2800.HK'
CN_benchmark = '159919.SZ'
tickers = ['BRK-B','LIT','ARKK','BIDU','DBC','REET','9988.HK', '0001.HK','2840.hk', US_benchmark , HK_benchmark, CN_benchmark]
for i in tickers:
    tmp = web.DataReader(i, 'yahoo', '1/1/2010', dt.date.today())
    Closeprice[i] = tmp['Adj Close']

#calculate the log return
##returns is a dataframe class
returns = np.log(Closeprice / Closeprice.shift(1))

df = pd. DataFrame()
equity_columns = []

# Get symbol history
for symbol in tickers:
    try:
        symbol_df = returns[symbol]
        df = pd.concat([df, symbol_df], axis=1)
        equity_columns.append(symbol)
    except:
        print('Exception with {}'.format(symbol))

df.columns = equity_columns

# Get correlation and sort by sum
sum_corr = df.corr().sum().sort_values(ascending=True).index.values

corr_matrix = df[sum_corr].corr()
print(corr_matrix)
corr_matrix.to_csv(r'corr.csv', index=True, header=True)

#plt.figure(figsize=(13, 8))
#cmap options: “RdYlGn_r”, “summer_r”, “Blues”, and “Greens”
#sns.heatmap(corr_matrix, annot=True, cmap="RdYlGn_r")
#plt.show()