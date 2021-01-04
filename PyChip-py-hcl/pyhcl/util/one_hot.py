from typing import List, Tuple, Any, Union
from pyhcl import *
from pyhcl.util.util import get_pyhcl_type
from pyhcl.util.math import *
from pyhcl.util.circuit_math import cirLog2


def _priorityMux(_in: List[Tuple[Bool, Any]]):
    if len(_in) == 1:
        return _in[0][1]
    return Mux(_in[0][0], _in[0][1], _priorityMux(_in[1:]))


def asBools(x: U) -> List[Bool]:
    return [x[i] for i in range(x.width)]


def PriorityMux(sel: List[Any], _in: List[Any]):
    return _priorityMux(list(zip(sel, _in)))


def PriorityEncoder(_in: Union[List[Any], U]) -> U:
    if isinstance(_in, list):
        return PriorityMux(_in, [U(i) for i in range(len(_in))])
    return PriorityEncoder(asBools(_in))


def PriorityEncoderOH(_in: Union[List[Any], U]) -> List[Bool]:

    def tabulate(n, f):
        return [f(i) for i in range(n)]

    def encode(_in):
        outs = tabulate(len(_in), lambda i: U(1 << i))
        _in.append(Bool(True))
        outs.append(U.w(len(_in))(0))
        return PriorityMux(_in, outs)

    if not isinstance(_in, list):
        return encode(list(map(lambda i: _in[i], [i for i in range(_in.width)])))

    enc = encode(_in)
    return tabulate(len(_in), lambda i: enc(i))


def UIntToOH(_in: U) -> U:
    return U(1) << _in


def OHToUInt(_in: Union[List[Any], U]) -> U:
    def apply(_in, width):
        if width <= 2:
            return cirLog2(_in, width)
        mid = 1 << (log2Ceil(width)-1)
        hi = _in[width-1: mid]
        lo = _in[mid-1: 0]
        return CatBits(hi.orR, apply(hi | lo, mid))

    if isinstance(_in, list):
        return apply(CatBits(*_in), len(_in))
    return apply(_in, _in.width)


if __name__ == "__main__":
    class Test(Module):
        io = IO(
            a=Input(U.w(32)),
            b=Output(U.w(32)),
        )
        r = Reg(U.w(10))
        io.b <<= OHToUInt(r & ~io.a)

    Emitter.dump(Emitter.emit(Test()), f"{__file__}.fir")

