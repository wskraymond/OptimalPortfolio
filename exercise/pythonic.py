
# ternary operation for conditional expression
x = 4
result = "A" if x < 0 else "B"
print(result)

# instead of def add(a,b), use lambda
add = lambda a,b : a+b

print(add(1,2))

# f for formatting
name = "xxx"
print(f"my name is {name}, x={x}")

#unpacking list or tuple
values = (1,2,3)
a,b,c = values
print(a,b,c)

#List comprehension
sqs = [i*i for i in range(1,5)]
print(sqs)

#zip
l1 = [1,2,3]
l2 = ['a','b','c', 'x']

for x, y in zip(l1,l2):
    print(x,y)

#map function
#long way
sqs2 = list(map(lambda x:x**2,l1))
#short way
sqs2 = [ x**2 for x in l1]

#filter function
#long way
even = list(filter(lambda x : x%2==0, l1))
#short way
even = [x for x in l1 if x%2==0]

# set
a = {1,2,3}
b = {3,4,5}
# Set Intersection
# long way
print(a.intersection(b))

# short way
print(a & b)

#Set Union
#long way
print(a.union(b))

#short way
print(a | b)

