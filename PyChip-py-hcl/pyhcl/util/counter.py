from pyhcl import *
from pyhcl.util.math import *
from pyhcl.util.wire import WireDefault
from typing import Union


class Counter:

    def __init__(self, r: Union[int, range]):
        if isinstance(r, int):
            r = range(r)
        self.delta = abs(r.step)
        self.width = max(log2Up(r.stop), log2Up(r.start + 1))
        if len(r) > 1:
            self.value = RegInit(U.w(self.width)(r.start))
        else:
            self.value = WireDefault(U.w(self.width), U(r.start))
        self.r = r

    def inc(self):
        if len(self.r) > 1:
            wrap = self.value == U(self.r.stop-1)
            if self.r.step > 0:
                self.value <<= self.value + U(self.delta)
            else:
                self.value <<= self.value - U(self.delta)
            # We only need to explicitly wrap counters that don't start at zero, or
            # end on a power of two. Otherwise we just let the counter overflow
            # naturally to avoid wasting an extra mux.
            if not (self.r.start == 0 and isPow2(self.r.stop-1+self.delta)):
                with when(wrap):
                    self.value <<= U(self.r.start)
            return wrap

        return Bool(True)


def CounterDefault(cond: Bool, n: int):

    c = Counter(range(n))
    wrap = WireDefault(Bool, Bool(False))
    with when(cond):
        wrap <<= c.inc()

    return c.value, wrap

