# Test program
import random
import datetime
import math

print("hello")

"""
The number of spaces in the indentation is variable, 
but all statements within the block must be indented the same amount. 
"""

# number
y = 5
x = 4

# string
myStr = "12345"
paragraph = """
this is a long sentence
"""
paragraph2 = '''
this is a short sentence
'''

# list
myList = ['abc', 23, float(0.2), int(222222222222)]  # can specify the data type explicitly

# Set
mySet = {'apple', 'orange'}

# tuple
myTuple = (12, True, "end")

# dictionary
myDict = {1: "A", "two": "B", 3.0: "C"}


# a class
class MyClass:
    """Common python class example"""

    myCount = 0

    def __init__(self, name, age):
        self.name = name
        self.age = age
        MyClass.myCount += 1

    def __len__(self):
        return 0

    def work(self):
        print(self.name, self.age)

    def __del__(self):
        class_name = self.__class__.__name__
        print(class_name, "GC")

    def __add__(self, other):
        return MyClass(other.name + self.name, other.age + self.age)

    def __str__(self):
        return self.name + "---" + str(self.age)


class Student(MyClass):
    """Student extends Myclass"""

    def __init__(self, name, age, score):
        super().__init__(name, age)
        self.score = score
        self.__suid = random.randrange(0, 1000)

    def __str__(self):
        return super().__str__() + "--" + str(self.score) + "--" + str(self.__suid)


class MyException(Exception):
    def __init__(self, args):
        self.args = args


obj = MyClass("test", 18)

if y > x:
    # del x
    print(type(x))
    print("convert x to float type = " + str(float(x)))

    # random number
    print("random number")
    print(random.randrange(1, 10))

    print(myStr[0])
    print(myStr[1:3])  # does not include element at index 3
    print(myStr[1:])
    print(myStr[:4])
    print(myStr * 2)
    print(myStr + "test")

    # boolean
    print(bool(''))
    print(bool([]))
    print(bool({}))
    print(bool(0))
    print(bool(None))
    print(bool(False))
    print(isinstance(x, int))
    print(bool(obj))

    # list
    print(len(myList))
    print(myList[0])
    print(myList[-4:-1])  # exclude index -1
    if 'abc' in myList:
        print("abc is in myList")
        myList.remove('abc')
    myList.append('end')
    myList.insert(0, 1)
    print(myList)
    myList.pop()  # remove last element if not specifed
    myList.pop(0)  # remove first element
    print(myList)
    del myList[1]  # remove element from list by reference(
    print(myList)

    myList2 = myList.copy()
    print(myList2)
    myList.clear()
    print(myList)
    myList3 = list(myList2)
    print(myList3)

    myList4 = myList2 + myList3
    print(myList4)

    myList4.extend(myList4)
    print(myList4)

    # set
    mySet.add("lemon")
    mySet.update(["Banana", "Strawberry"])
    print(len(mySet))
    print(mySet)
    if 'lemon' in mySet:
        print("lemon is in mySet")

    mySet.union(mySet)
    print(mySet)

    # myTuple
    # myTuple[0] = 1 # error
    oneTuple = ("new",)  # remember to add comma for one item
    myTuple3 = myTuple + oneTuple
    print(myTuple3)

    # myDict
    myDict[1] = "Start"
    print(myDict.keys())
    print(myDict.values())
    for key in myDict:
        print(myDict[key])

    if 1 in myDict:
        for key, value in myDict.items():
            print(key, value)

    print("remove from dict")
    myDict.pop(1)
    print("myDict", myDict)
    myDict2 = {1: {2: {3: "end"}}}
    print(myDict2)

    # if elif else
    if len(myDict2) == 2:
        print(myDict2[1])
    elif len(myDict2[1]) == 1:
        print(myDict2[1][2])  # it is not index, but key!!!!!
        del myDict2[1][2]
    else:
        print("end")

    print(myDict2)
    myDict2.clear()
    print(myDict2)
    del myDict2  # completely delete
    # print(myDict2)  #error

    # while loop
    # break , continue
    i = 0
    while i < 6:
        print(i)
        while i < 6:
            if i == 3:
                break
            i += 1
        i += 1
    else:
        print("break while")

    # range
    for i in range(0, 4, 2):
        for j in range(0, i + 1, 1):
            print(i, j)
    else:
        print("end loop")

    '''
    def functionname( parameters ):
       "function_docstring"
       function_suite
       return [expression]
    '''


    def myFunc(a="A"):
        print(a)


    def myFunc2(*kids):
        print('myFunc2', type(kids))
        for x in kids:
            print(x)


    def myFunc3(**kids):
        print('myFunc3', type(kids))
        for key in kids:
            print(kids[key])

        return 5 * 5


    def emptyFunc():
        pass


    myFunc(a="kk")
    myFunc2("A", "B")
    emptyFunc()
    print(myFunc3(kid1=1, kid2=2))


    def multiplierOf(mult):
        return lambda a: a * mult


    doubleFunc = multiplierOf(2)
    tripleFunc = multiplierOf(3)

    print(doubleFunc(4))
    print(tripleFunc(3))

    newObj = MyClass("human", 10)
    print(newObj + obj)

    obj.work()
    obj.age = 27
    del obj.name
    # print(obj.name) # error
    print(obj.__doc__)
    print(obj.__module__)

    obj1 = obj
    obj2 = obj1
    print(id(obj), id(obj1), id(obj2))
    print(id(obj) == id(obj1) and id(obj1) == id(obj2))
    print("# Decrease ref. count  of myClass object")
    del obj
    print("# Decrease ref. count  of myClass object")
    del obj1
    print("# Decrease ref. count  of myClass object")
    del obj2

    sObj = Student("peter", 24, 15)
    print(sObj)
    # print(sObj.__suid) # unable to access __suid
    print("sObj._Student__suid", sObj._Student__suid)

    # date
    today = datetime.datetime.now()
    print(today)
    print("day of week=", today.strftime("%A"))
    print(datetime.datetime(2020, 9, 23, 16, 29, 0))
    print(math.log(10, math.e))

    try:
        f = open("abc.csv")
        f.write("hello word")
    except IOError as e:
        print("IOError", e)
    finally:
        print("finally")

    print("------------------------end of program--------------------")
