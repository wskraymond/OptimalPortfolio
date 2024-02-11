import pandas as pd
import numpy as np
import xarray as xr

s = pd.Series()
print(s)

# create using Array
# default indexing
data = np.array(['a', 'b', 'c', 'd'])
s = pd.Series(data)
print(s)

# assigned index
data = np.array(['a', 'b', 'c', 'd'])
s = pd.Series(data, index=[100, 101, 102, 103])
print(s)

# create using dict
# without assigned index, dict key as index , value as value
data = {'a': 0., 'b': 1., 'c': 2.}
s = pd.Series(data)
print(s)

# with assigned index, map entry will map to each index by its key
# if missing , then assign NaN
data = {'a': 0., 'b': 1., 'c': 2.}
s = pd.Series(data, index=['b', 'c', 'd', 'a'])
print(s)

# Create using scaler

# Index is required
s = pd.Series(5, index=[0, 1, 2, 3])
print(s)

# Retrieving like array using integer-based position
s = pd.Series([1, 2, 3, 4, 5], index=['a', 'b', 'c', 'd', 'e'])

print(s[-3:])  # retrieve the last three element

# Retrieving using label (Series's index)
print(s['a'])  # A Series is like a fixed-size dict in that you can get and set values by index label

# Retrieve multiple elements using a list of index label values.
print(s[['a', 'c', 'd']])

# Data Frame
df = pd.DataFrame()
print(df)

# single list
data = [1, 2, 3, 4, 5]
df = pd.DataFrame(data)
print(df)

# list of list , given column name
data = [['Alex', 10], ['Bob', 12], ['Clarke', 13]]
df = pd.DataFrame(data, columns=['Name', 'Age'])
print(df)

# specify dType
df = pd.DataFrame(data, columns=['Name', 'Age'], dtype=float)
print(df)  # the dtype parameter changes the type of Age column to floating point

# dict of equal-sized list/array
data = {'Name': ['Tom', 'Jack', 'Steve', 'Ricky'], 'Age': [28, 34, 29, 42]}
df = pd.DataFrame(data)
print(df)

# dict , given the same number of indices for rows
df = pd.DataFrame(data, index=['rank1', 'rank2', 'rank3', 'rank4'])
print(df)

# List of dict
# The dictionary keys are by default taken as column names.
data = [{'a': 1, 'b': 2}, {'a': 5, 'b': 10, 'c': 20}]
df = pd.DataFrame(data)
print(df)  # NaN (Not a Number) is appended in missing areas

# given the same number of indices for rows
data = [{'a': 1, 'b': 2}, {'a': 5, 'b': 10, 'c': 20}]
df = pd.DataFrame(data, index=['first', 'second'])
print(df)

# given that row indices + column indices
data = [{'a': 1, 'b': 2}, {'a': 5, 'b': 10, 'c': 20}]

df1 = pd.DataFrame(data, index=['first', 'second'],
                   columns=['a', 'b'])  # With two column indices, values same as dictionary keys
print(df1)

df2 = pd.DataFrame(data, index=['first', 'second'],
                   columns=['a', 'b1'])  # With two column indices with one index with other name
print(df2)  # a column index other than the dictionary key; thus, appended the NaN’s in place.

# Dict of Series
# Dict key as column indices, Series index as row indices
d = {'one': pd.Series([1, 2, 3], index=['a', 'b', 'c']),
     'two': pd.Series([1, 2, 3, 4], index=['a', 'b', 'c', 'd'])}

df = pd.DataFrame(d)
print(df)  # there is no label ‘d’ passed, but in the result, for the d label, NaN is appended with NaN

# Column Selection
print(df['one'])

# Adding a new column by passing as Series
df['three'] = pd.Series([10, 20, 30], index=['a', 'b', 'c'])
print(df)

# Adding a new column using the existing columns in DataFrame
df['four'] = df['one'] + df['three']
print(df)

# Column Deletion
# del cmd
del df['one']

# pop func
df.pop('two')

print(df)

# Row Selection
# loc func is passed a row index
print(df.loc['b']) # The result is a series with labels as column names of the DataFrame

# iloc func is passed a integer-based position
print(df.iloc[2])

# Slice rows
print(df[2:4])

# addition of rows
# append func
df = pd.DataFrame([[1, 2], [3, 4]], columns = ['a','b'])
df2 = pd.DataFrame([[5, 6], [7, 8]], columns = ['a','b'])

df = df.append(df2)
print(df) # row indices doesn't change

# Deletion of rows
# If label is duplicated, then multiple rows will be dropped.
# drop func
df = df.drop(1)
print(df)

# Panel is deprecated
# use xarray instead
da = xr.DataArray([9, 0, 2, 1, 0],
                  dims=['x'],
                  coords={'x': [10, 20, 30, 40, 50]})

print(da)
