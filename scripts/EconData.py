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
#Real GDP USA
#https://www.econdb.com/
f = web.DataReader('ticker=RGDPUS', 'econdb')
print(f)


#Financial data
#https://pydata.github.io/pandas-datareader/readers/alphavantage.html
#https://www.alphavantage.co/documentation/
a = web.get_sector_performance_av(api_key="ALPHAVANTAGE_API_KEY").head()
print(a)



