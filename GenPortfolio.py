import pandas as pd
import numpy as np
import pandas_datareader.data as web
import matplotlib.pyplot as plt
import scipy.optimize as solver
import datetime as dt
from functools import reduce


#use pandas_datareader to get the close price data from Yahoo finance giving the stock tickets and date
Closeprice = pd.DataFrame()
tickers = ['BRK-B','LIT','ARKK','BIDU','MSOS','ARKQ','DBC','BABA']
for i in tickers:
    tmp = web.DataReader(i, 'yahoo', '1/1/2010', dt.date.today())
    print
    Closeprice[i] = tmp['Adj Close']

#calculate the log return
##returns is a dataframe class
returns = np.log(Closeprice / Closeprice.shift(1))

np.random.seed(42)
num_ports = 6000
all_weights = np.zeros((num_ports, len(tickers)))
ret_arr = np.zeros(num_ports)
vol_arr = np.zeros(num_ports)
sharpe_arr = np.zeros(num_ports)

for x in range(num_ports):
    # Weights
    weights = np.array(np.random.random(len(tickers)))
    weights = weights/np.sum(weights)

    # Save weights
    all_weights[x,:] = weights

    # Expected return
    ret_arr[x] = np.sum( (returns.mean() * weights * 252))

    # Expected volatility
    vol_arr[x] = np.sqrt(np.dot(weights.T, np.dot(returns.cov()*252, weights)))

    # Sharpe Ratio
    sharpe_arr[x] = ret_arr[x]/vol_arr[x]


maxSR=sharpe_arr.max()
maxIndex=sharpe_arr.argmax()
maxSRReturn=ret_arr[maxIndex]
maxSRVol=vol_arr[maxIndex]
optimizedW=all_weights[maxIndex]

print("maxSR", maxSR, "maxSRReturn", "maxSRReturn", maxSRReturn,"maxSRVol",  maxSRVol, "optimizedW", optimizedW)

#return and volatility for the simulation with the maximum Sharpe ratio.
plt.figure(figsize=(12,8))
plt.scatter(vol_arr, ret_arr, c=sharpe_arr, cmap='viridis')
plt.colorbar(label='Sharpe Ratio')
plt.xlabel('Volatility')
plt.ylabel('Return')
plt.scatter(maxSRVol, maxSRReturn, c='red', s=50)  # red dot
plt.show()
