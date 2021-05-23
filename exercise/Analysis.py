import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import pandas
from sklearn import linear_model

# mean , std
arr = np.array([99, 86, 87, 88, 111, 86, 103, 87, 94, 78, 77, 85, 86])
print(np.mean(arr))
print(np.median(arr))
print(stats.mode(arr))
print(np.std(arr))
print(np.var(arr))

# Data set generation => population
x = np.random.normal(np.mean(arr), np.std(arr), 100000)
plt.hist(x, 100)
#plt.show()

# linear regression
x = [5, 7, 8, 7, 2, 17, 2, 9, 4, 11, 12, 9, 6]
y = [99, 86, 87, 88, 111, 86, 103, 87, 94, 78, 77, 85, 86]

slope, intercept, r, p, std_err = stats.linregress(x, y)


def linearFunc(i):
    return intercept + slope * i


expectedY = list(map(linearFunc, x))

plt.scatter(x, y)
plt.plot(x, expectedY)
#plt.show()

print("coefficient", r)


#Pandas, multiple regression
df = pandas.read_csv("cars.csv")
X = df[['Weight', 'Volume']]
y = df['CO2']

regr = linear_model.LinearRegression()
regr.fit(X, y)

print(regr.coef_)

predictedCO2 = regr.predict([[2300, 1300]])
predictedCO2_2 = regr.predict([[3300, 1300]])

print("2300, 1300" , predictedCO2)
print("3300, 1300" , predictedCO2_2)


