import math
from math import log2
from functools import reduce
from pyhcl import *


def log2Ceil(x):
    return math.ceil(math.log(x, 2))


def log2Up(x):
    return max(log2Ceil(x), 1)


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
    return {k: f(v) for k, v in m.items()}


def Cat(*args):
    return CatBits(*args)


def Fill(n, x):
    return Cat(*[x for _ in range(n)])


def get_from(l, v):
    m = {}
    for i in range(len(l)):
        m[U(i)] = l[i]
    m[...] = U(0)
    return LookUpTable(v, m)


def orRsize(x, size):
    ret = U(0)
    for i in range(size):
        ret = ret | x[i]
    return ret
    

def orR(x):
    from pyhcl.core._repr import Index
    from pyhcl.dsl.cdatatype import INT
    from pyhcl.core._repr import Cat
    if isinstance(x, Index):
        ss = x.index
        if isinstance(ss, slice):
            size = ss.start - ss.stop + 1
        else:
            size = 1
    elif issubclass(x.__class__, INT):
        size = x.width
    elif isinstance(x, list):
        size = len(x)

    return orRsize(x, size)


def isPow2(x):
    return not (x & (x-1))


def partition(f, m):
    if isinstance(m, dict):
        yes = {}
        no = {}
        for k, v in m.items():
            if f(k, v):
                yes[k] = v
            else:
                no[k] = v
        return yes, no


def foldLeft(f, l, v):
    ret = v
    for item in l:
        ret = f(ret, item)
    return ret
        
    
def distinct(l):
    return list(set(l))


def forall(f, l):
    for i in l:
        if not(f(i)):
            return False
    return True


def asTypeOf(x, t):
    from pyhcl.dsl.cdatatype import INT
    ret = t()
    start = t.getWidth() - 1
    for k, v in ret.__dict__.items():
        if issubclass(v, INT):
            ret.__dict__[k] = x[start: start+v.width]
            start += v.width
    return ret


def vec(n, v):
    class ll(list):
        def map(self, f):
            return ll(map(f, self))
        @property
        def asUInt(self):
            return CatBits(*self)
        @property
        def size(self):
            return len(self)

    return ll([v for _ in range(n)])


def isOneOf(v, *args):
    m = {}
    for k in args:
        m[k] = U(1)
    m[...] = U(0)
    return LookUpTable(v, m)


def flip(m):
    pass


def Decoupled(m):
    pass


def DecoupledHelper(m):
    pass


def UIntToOH(i):
    pass


def OHToU(i):
    pass


class cls_or_insmethod(classmethod):
    def __get__(self, instance, type_):
        descr_get = super().__get__ if instance is None else self.__func__.__get__
        return descr_get(instance, type_)

