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

margin_rate = 1
Closeprice = pd.DataFrame()
tickers = {'BRK-B','LIT','ARKK','BIDU','MSOS','ARKQ','DBC','BABA'}
US_benchmark = 'SPY'
HK_benchmark = '2800.HK'
CN_benchmark = '159919.SZ'
benchmarks = {US_benchmark, HK_benchmark, CN_benchmark}
# for i in tickers.union(benchmarks):
#     tmp = web.DataReader(i, 'yahoo', '1/1/2010', dt.date.today())
#     Closeprice[i] = tmp['Adj Close']

#Real GDP USA
#https://www.econdb.com/
f = web.DataReader('ticker=RGDPUS', 'econdb')
print(f)


#Financial data
#https://pydata.github.io/pandas-datareader/readers/alphavantage.html
#https://www.alphavantage.co/documentation/
a = web.get_sector_performance_av(api_key="ALPHAVANTAGE_API_KEY").head()
print(a)



