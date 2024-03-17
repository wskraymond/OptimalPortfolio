import pandas as pd
import numpy as np
import pandas_datareader.data as web
import matplotlib.pyplot as plt
import scipy.optimize as solver
import datetime as dt
from functools import reduce
import math

table=pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
df = table[0]

print(set(df['Symbol'].to_list()))


table=pd.read_html('https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average')
df = table[1]
print(set(df['Symbol'].to_list()))

#https://bullishbears.com/nikkei-225-stocks-list/
nk_df=pd.read_csv("csv/nikkei_225_list.csv")
stockCode = filter(lambda str: str.isnumeric(), nk_df['Symbol'].to_list())
tickers = set([s + '.T' for s in stockCode])
print(tickers)