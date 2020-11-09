import math
from math import log2


def log2Ceil(x):
    return math.ceil(math.log(x, 2))


def flatten(l):
    return [y for x in l for y in x]


def groupBy(f, l):
    ret = {}
    for item in l:
        if f(item) not in ret:
            ret[f(item)] = []
        ret[f(item)].append(item)
    return ret


def mapValues(f, m):
    return {k, f(v) for k, v in m.items()}


def Fill(n, x):
    pass


def isPow2(x):
    return not (x & ~x)
