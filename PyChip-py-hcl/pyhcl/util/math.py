import math


def log2Ceil(x):
    return math.ceil(math.log(x, 2))


def log2Up(x):
    return max(log2Ceil(x), 1)


def isPow2(x):
    return not (x & (x-1))    

