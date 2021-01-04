from __future__ import annotations
import math
from math import log2
from functools import reduce
from pyhcl import *
from pyhcl.util import *
from typing import List


def asUInt(x):
    return CatBits(*[i for i in x])


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


def vec(n, v):

    class ll(list):
        def map(self, f):
            return ll(map(f, self))
        def filter(self, f):
            return ll(filter(f, self))
        def foreach(self, f):
            for v in self:
                f(v)
            return self
        @property
        def min(self):
            return min(self)
        @property
        def max(self):
            return max(self)
        @property
        def asUInt(self):
            return CatBits(*self)
        @property
        def size(self):
            return len(self)
        @property
        def reverse(self):
            new = ll(self)
            new.reverse()
            return new
        @property
        def distinct(self):
            return ll(set(self))
        def reduce(self, f):
            return reduce(f, self)
        def exists(self, f):
            for v in self:
                if f(v):
                    return True
            return False
        def contains(self, v):
            return v in self
        def find(self, f):
            for v in self:
                if f(v):
                    return v
            return None
        def foldLeft(self, v):
            def helper(f):
                ret = v
                for item in self:
                    ret = f(ret, item)
                return ret
            return helper
        def scanLeft(self, v):
            def helper(f):
                ret = ll()
                s = v
                ret.append(s)
                for item in self:
                    s = f(s, item)
                    ret.append(s)
                return ret
            return helper

    return ll([v for _ in range(n)])


def isOneOf(v, *args):
    m = {}
    for k in args:
        m[k] = U(1)
    m[...] = U(0)
    return LookUpTable(v, m)


class cls_or_insmethod(classmethod):
    def __get__(self, instance, type_):
        descr_get = super().__get__ if instance is None else self.__func__.__get__
        return descr_get(instance, type_)


def asTypeOf(x, typ):
    new = Wire(get_pyhcl_type(typ))
    wx  = Wire(get_pyhcl_type(x))
    start = typ.width - 1
    for k, v in new.typ._kv.items():
        attr = new.__getattribute__(k)
        attr <<= wx[start: start-v.width]
        start -= v.width
    return new


if __name__ == "__main__":
    l = vec(10, 1)
    for i in range(10):
        l[i] = i
    print(l.foldLeft(0)(lambda x, y: x+y))
    print(l.scanLeft(0)(lambda x, y: x+y))
