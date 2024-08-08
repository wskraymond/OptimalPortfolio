# Optimal Portfolio

Features
1. read stock adjusted close price from market data source ( IB Data Or Tiingo)
2. risk and return 
3. Tangent portfolio for optimization from N stocks
4. Beta 
5. Yield Curve

![alt text](doc/2023_spy_optimal.png?raw=true "GenPortfolio3.py")
![alt text](doc/correlation.png?raw=true "Correlation.py")
![alt text](doc/yield_curve.png?raw=true "GenYieldCurve.py")

Rolling Statistics
1) optimal portfolio rolling window over 5 years from 2010
```
py GenRollingPortfolioFromDB.py --startdate 01/01/2010 --holdingPeriodYear 5 --cmd o
```
![alt text](doc/2010_HPR_5_YR_alloc.png?raw=true "Allocation for roll over 5 years from 2010")
![alt text](doc/2010_HPR_5_YR_ratio.png?raw=true "Ratio for roll over 5 years from 2010")
2) Exponential Moving Average for optimal portfolio
```
py GenRollingPortfolioFromDB.py --startdate 01/01/2005 --holdingPeriodYear 5 --cmd o_avg
```
   ![alt text](doc/EMW_Allocation.png?raw=true "Allocation for roll over 5 years from 2005")
   ![alt text](doc/EMW_Ratio.png?raw=true "Ratio for roll over 5 years from 2005")
3) Rolling Correlation
```
py GenRollingPortfolioFromDB.py --startdate 01/01/2005 --holdingPeriodYear 5 --cmd corr_avg
```
![alt text](doc/rolling_corr.png?raw=true "Rolling Correlation over 5 years from 2005")

4) Rolling Beta
```
py GenRollingPortfolioFromDB.py --startdate 01/01/2005 --holdingPeriodYear 5 --cmd beta_avg
```
![alt text](doc/rolling_beta.png?raw=true "Rolling Beta over 5 years from 2005")
5) Rolling Risk
```
py GenRollingPortfolioFromDB.py --startdate 01/01/2005 --holdingPeriodYear 5 --cmd std_avg
```
![alt text](doc/rolling_std.png?raw=true "Rolling Risk over 5 years from 2005")

# Market Data subscription
### Tiingo market data (limited usage)
```python
pdr.get_data_tiingo(symbols=i, start=args.startdate, end=dt.date.today(), retry_count=5, api_key=apiToken)
```
### Download the IB Python native API
You can download the Python Native API by navigating to the Interactive Brokers website and by going to Technology – Trading APIs – Get API Software, or by following this link – http://interactivebrokers.github.io/

Make sure to select API version 9.73 or higher as anything prior to that does not have the Python source files needed. Also, you should be using Python version 3.1 or higher.

Run the downloaded msi file and go through the setup wizard. This will copy the required Python source files to your hard drive. Once completed, navigate over to the directory that you specified in the installer and drill down to this directory – /TWS API/source/pythonclient. In this folder, run the python3 setup.py install file to install the API as a package.

Congratulations! You’ve now installed the IB API. Just to make sure it is installed correctly, go into your Python terminal and type in import ibapi. If no errors appear, the install was successful.

The IB API installer will install a few files that enable compatibility with Excel and also make a registry change in the process. If you’re looking to avoid that, check out the instructions for setting up the API in Linux or on a Mac, the method works just as well for Windows.

```python
#https://interactivebrokers.github.io/tws-api/historical_bars.html
#https://interactivebrokers.github.io/tws-api/historical_bars.html#hd_what_to_show
# TRADES data is adjusted for splits, but not dividends.
# ADJUSTED_LAST data is adjusted for splits and dividends. Requires TWS 967+.
app.reqHistoricalData(
      reqId=id,
      contract=contract,
      endDateTime="",
      durationStr="30 Y",
      barSizeSetting="1 day",
      whatToShow="ADJUSTED_LAST",
      useRTH=0,
      formatDate=1,
      keepUpToDate=False,
      chartOptions=[],
) 
```

## Load IB Data into cassandra database
1. setup cassandra container in docker using cassandra_docker/cassandra.yml , and create keyspace
```
   -- Create a keyspace
   CREATE KEYSPACE IF NOT EXISTS store WITH REPLICATION = { 'class' : 'SimpleStrategy', 'replication_factor' : '1' };
```
2. start IB Gateway 10.19
3. Run IBData.py
```
py IBData.py
```
4. check result using cqlsh in docker container
```
# cqlsh
Connected to Test Cluster at 127.0.0.1:9042
[cqlsh 6.1.0 | Cassandra 4.1.5 | CQL spec 3.4.6 | Native protocol v5]
Use HELP for help.
cqlsh> select * from store.DailyPrice;

 ticker | date       | close | created_at                      | currency                        | high  | low   | name | updated_at                      | year
--------+------------+-------+---------------------------------+---------------------------------+-------+-------+------+---------------------------------+------
    DBC | 2024-07-30 | 22.04 | 2024-07-30 17:12:15.378000+0000 | {code: 'USD', country: 'SMART'} | 22.04 | 22.04 |  DBC | 2024-07-30 17:12:15.378000+0000 | 2024
    DBC | 2024-07-29 | 22.14 | 2024-07-30 17:12:15.378000+0000 | {code: 'USD', country: 'SMART'} | 22.34 | 22.05 |  DBC | 2024-07-30 17:12:15.378000+0000 | 2024
    DBC | 2024-07-26 | 22.24 | 2024-07-30 17:12:15.378000+0000 | {code: 'USD', country: 'SMART'} | 22.39 | 22.19 |  DBC | 2024-07-30 17:12:15.378000+0000 | 2024
    DBC | 2024-07-25 | 22.47 | 2024-07-30 17:12:15.378000+0000 | {code: 'USD', country: 'SMART'} | 22.52 | 22.21 |  DBC | 2024-07-30 17:12:15.378000+0000 | 2024
    DBC | 2024-07-24 | 22.38 | 2024-07-30 17:12:15.378000+0000 | {code: 'USD', country: 'SMART'} |  22.6 | 22.38 |  DBC | 2024-07-30 17:12:15.378000+0000 | 2024
```
## virtual environment setup
1. pip install virtualenv
2. py -m venv myenv  #venv for python3 , env folder name: myenv
3. cd myenv/Scripts
4. .\pip.exe install -r ..\..\requirements.txt  #using pip in myenv/Scripts , here is window example
5. .\pip.exe list
6. configure intellij to myenv 
      refer to https://www.jetbrains.com/help/pycharm/creating-virtual-environment.html#python_create_virtual_env
     

# Virutalenv Activate
```bash
.\myenv\Scripts\activate.bat  #set Env to virutalenv Path 
```

# Run
```bash
python .\scripts\GenPortfolio3.py 
```
      

## Tips for Panda performance improvement

1. Python’s dynamic nature makes it slower than compiled languages. This issue is exacerbated in scientific computing because we run simple operations millions of times.
2. Don’t loop over your data. Instead, vectorize your operations (remember Hector Vector).
3. You can use numpy directly by calling .to_numpy() on the Dataframe, which can be even faster.
4. Choose the smallest possible numerical dtypes, use categoricals, and prefer float32 over the newish nullable dtypes (for now).
5. Use parquet to store your data. Use snappy compression (or none at all) during development, resorting to gzip for long-term archival.


### dtype in DataFrames
In pandas DataFrames, the dtype is a critical attribute that specifies the data type for each column. 
Therefore, selecting the appropriate dtype for each column in a DataFrame is key.

![alt text](doc/numpy-array.avif?raw=true "numpy")
![alt text](doc/python-list.avif?raw=true "python")

#### The object type
Because pandas stores strings as objects, it has to fall back on slow Python arrays. 
In contrast to numpy, a Python `list` has a pointer to a memory-contiguous buffer 
of **pointers**, which point to objects stored in memory, but which also reference data stored in other locations.


#### Numeric
Regarding ints and floats, downcasting is the key to saving memory. 
Pandas supports 8, 16, 32, and 64-bit signed and unsigned integers and 16, 32, 
and 64-bit floats. By default, it opts to use 64-bit variants for both types.

Downcasting numeric types into c primitive types.
```python
n = 100_000

df = pd.DataFrame({
        "uint8": np.random.randint(10, 20, n),
        "uint32": np.random.randint(100_000, 200_000, n),
        "int16": np.random.randint(1_000, 2_000, n) * np.random.choice((-1, 1), n),
        "float32": np.random.uniform(100_000, 200_000, n),
    }
)

df_downcasted = (
    df
    .apply(pd.to_numeric, downcast="float")
    .apply(pd.to_numeric, downcast="integer")
    .apply(pd.to_numeric, downcast="unsigned")
)
```


###### Reference
https://tryolabs.com/blog/2023/02/08/top-5-tips-to-make-your-pandas-code-absurdly-fast
