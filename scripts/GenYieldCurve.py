from pandas_datareader.data import DataReader as dr
import matplotlib.pyplot as plt
import datetime as dt

syms = ['DGS30', 'DGS20','DGS10', 'DGS5', 'DGS2', 'DGS1MO', 'DGS3MO']
yc = dr(syms, 'fred','1/1/2019', dt.date.today()) # could specify start date with start param here
names = dict(zip(syms, ['30yr', '20yr', '10yr', '5yr', '2yr', '1m', '3m']))
yc = yc.rename(columns=names)
yc = yc[['1m', '3m', '2yr', '5yr', '10yr', '20yr', '30yr']]

print(yc)

yc.loc['2021-06-28'].plot(label='Jun 28')
yc.loc['2021-05-28'].plot(label='May 28')
# yc.loc['2021-04-28'].plot(label='Apr 28')
yc.loc['2019-01-02'].plot(label='Jan 01, 2019', color='red')
plt.legend(loc=0)
plt.show()

