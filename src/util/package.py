from pyhcl import *
from typing import List


def groupByIntoSeq(xs):
    m = {}
    def helper(f):
        for x in xs:
            key = f(x)
            if key not in m:
                m[key] = []
            m[key].append(x)
        return [(k, v) for k, v in m.items()]
    return helper


def padTo(x: U, n: int) -> U:
    from helper.common import _get_size
    width = _get_size(x)
    assert(width <= n)
    if width == n:
        return x
    return CatBits(U.w(n-width)(0), x)


def extract(x, hi: int, lo: int) -> U:
    assert hi >= lo-1
    if (hi == lo-1): return U(0)
    return x[hi: lo]


def OH1ToOH(x: int) -> int:
    return (x << 1 | U(1)) & ~Cat(U.w(1)(0), x)


def OH1Toint(x: int) -> int:
    return OHToint(OH1ToOH(x))


def intToOH1(x: int, width: int = None) -> int:
    if not width:
        return intToOH1(x, (1 << x.width) - 1)
    return ~(S.w(width)(-1).asint << x)[width-1: 0]


def OptimizationBarrier(_in):
    class helper(Module):
        io = IO(
            x = Input(_in),
            y = Output(_in),
        )
        io.y <<= io.x
    barrier = helper()
    barrier.io.x <<= _in
    return barrier.io.y


def orR(seq: List[Bool]) -> Bool:
    from functools import reduce
    return reduce(lambda x, y: x|y, seq)


def andR(seq: List[Bool]) -> Bool:
    from functools import reduce
    return reduce(lambda x, y: x&y, seq)


def xorR(seq: List[Bool]) -> Bool:
    from functools import reduce
    return reduce(lambda x, y: x^y, seq)


if __name__ == "__main__":
    print(groupByIntoSeq([1,2,3])(lambda x: x+1))
