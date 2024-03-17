import numpy as np

arr = np.array([1, 2, 3, 4], dtype='i4')
newArr = arr.astype('S')

print(type(arr))
print(type(newArr))
print(arr)
print(newArr)

x = arr.copy()
x[0] = 99
y = arr.view()
y[1] = 99

print('x', x)
print('x.base', x.base)
print('y', y)
print('y.base', y.base)

arr2D = np.array([[1, 2, 3, 4], [5, 6, 7, 8]])
print(arr2D[0, 0])  # i = 0, j=0 element
print(arr2D.ndim)  # dimension
print(arr2D.shape)

for row in arr2D:
    for column in row:
        print(column)

# 1 loop for n-D array
for el in np.nditer(arr2D):
    print(el)

for index, el in np.ndenumerate(arr):
    print(index, el)

arr2 = np.array([1, 2, 3, 4, 5,6,7,8])
transformed = arr2.reshape(2,4)
print(transformed)


# Python list to Numpy Array
a = [0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25]
a = np.array(a)
print(a.shape)

a = a.T
print(a)
print(a.shape)
