from pyhcl import *
from pyhcl.util.util import get_pyhcl_type
from pyhcl.util.math import *


divideAndConquerThreshold = 4


def cirLog2(x: U, width: int = None) -> U:

    if not width:
        width = x.width
    if width < 2:
        return U(0)
    if width == 2:
        return x[1]
    if width <= divideAndConquerThreshold:
        return Mux(x[width-1], U(width-1), cirLog2(x, width-1))

    mid = 1 << (log2Ceil(width) - 1)
    hi = x[width-1: mid]
    lo = x[mid-1: 0]
    useHi = hi.orR
    return CatBits(useHi, Mux(useHi, cirLog2(hi, width-mid), cirLog2(lo, mid)))

