#Optimal Portfolio
python 

1. read stock close price from data source
2. generate risk and return data 
3. do the analysis to find out the tangent portfolio
4. excel read csv file input and your own position for portfolio management

![alt text](doc/piechart.png?raw=true "GenPortfolio3.py")
![alt text](doc/correlation.png?raw=true "Correlation.py")
![alt text](doc/yield_curve.png?raw=true "GenYieldCurve.py")



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


###dtype in DataFrames
In pandas DataFrames, the dtype is a critical attribute that specifies the data type for each column. 
Therefore, selecting the appropriate dtype for each column in a DataFrame is key.

![alt text](doc/numpy-array.avif?raw=true "numpy")
![alt text](doc/python-list.avif?raw=true "python")

####The object type
Because pandas stores strings as objects, it has to fall back on slow Python arrays. 
In contrast to numpy, a Python `list` has a pointer to a memory-contiguous buffer 
of **pointers**, which point to objects stored in memory, but which also reference data stored in other locations.


####Numeric
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
