from __future__ import annotations
from pyhcl import *
from tile.Core import *
from helper.test import *


class PMPConfig(Bundle):
    def __init__(self):
        Bundle.__init__(self,
            l = Bool,
            res = U.w(2),
            a = U.w(2),
            x = Bool,
            w = Bool,
            r = Bool,
        )


class PMPReg(CoreBundle):
    def __init__(self, **kwargs):
        CoreBundle.__init__(self,
            cfg = PMPConfig(),
            addr = U.w(paddrBits - PMP.lgAlign),
            **kwargs
        )

    def reset(self):
        self.cfg.a <<= U(0)
        self.cfg.l <<= U(0)

    @property
    def readAddr(self):
        if (pmpGranularity.log2 == PMP.lgAlign):
            return self.addr
        mask = U((BigInt(1) << (pmpGranularity.log2 - PMP.lgAlign)) - 1)
        return Mux(napot, addr | (mask >> 1), ~(~addr | mask))

    @property
    def napot(self): return self.cfg.a[1]

    @property
    def torNotNAPOT(self): return self.cfg.a[0]

    @property
    def tor(self): return ~self.napot & self.torNotNAPOT

    @property
    def cfgLocked(self): return self.cfg.l

    def addrLocked(self, _next: PMPReg): return self.cfgLocked | _next.cfgLocked & _next.tor


class PMP(PMPReg):

    @classmethod
    def apply(cls, reg: PMPReg):
        w = Wire(PMP())
        w.cfg <<= reg.cfg
        w.addr <<= reg.addr
        w.mask <<= pmp.computeMask
        return w

    def __init__(self):
        PMPReg.__init__(self,
            mask = U.w(paddrBits)
        )

    @property
    def computeMask(self):
        base = Cat(self.addr, self.cfg.a[0]) | ((pmpGranularity - 1) >> lgAlign)
        return Cat(base & ~(base + 1), U((1 << lgAlign) - 1))

    @property
    def comparand(self): return U(~(~(self.addr << lgAlign) | (pmpGranularity - 1)))

    def pow2Match(self, x: U, lgSize: U, lgMaxSize: int):
        def eval(self, a: U, b: U, m: U): return ((a ^ b) & ~m) == 0
        if (lgMaxSize <= pmpGranularity.log2):
            return eval(x, self.comparand, self.mask)
        else:
            # break up the circuit; the MSB part will be CSE'd
            lsbMask = self.mask | UIntToOH1(lgSize, lgMaxSize)
            msbMatch = eval(x >> lgMaxSize, self.comparand >> lgMaxSize, self.mask >> lgMaxSize)
            lsbMatch = eval(x[lgMaxSize-1: 0], self.comparand[lgMaxSize-1: 0], lsbMask[lgMaxSize-1: 0])
            return msbMatch & lsbMatch

    def boundMatch(self, x: U, lsbMask: U, lgMaxSize: int):
        if (lgMaxSize <= pmpGranularity.log2):
            return x < self.comparand
        else:
            # break up the circuit; the MSB part will be CSE'd
            msbsLess = (x >> lgMaxSize) < (self.comparand >> lgMaxSize)
            msbsEqual = ((x >> lgMaxSize) ^ (self.comparand >> lgMaxSize)) == 0
            lsbsLess =    (x[lgMaxSize-1: 0] | lsbMask) < self.comparand[lgMaxSize-1: 0]
            return msbsLess | (msbsEqual & lsbsLess)

    def lowerBoundMatch(self, x: U, lgSize: U, lgMaxSize: int):
        return ~self.boundMatch(x, UIntToOH1(lgSize, lgMaxSize), lgMaxSize)

    def upperBoundMatch(self, x: U, lgMaxSize: int):
        return self.boundMatch(x, U(0), lgMaxSize)

    def rangeMatch(self, x: U, lgSize: U, lgMaxSize: int, prev: PMP):
        return prev.lowerBoundMatch(x, lgSize, lgMaxSize) & self.upperBoundMatch(x, lgMaxSize)

    def pow2Homogeneous(self, x: U, pgLevel: U):
        maskHomogeneous = self.pgLevelMap(
            lambda idxBits: Bool(False) if (idxBits > pself.addrBits) else self.mask(idxBits - 1))[pgLevel]
        return (maskHomogeneous | 
                (self.pgLevelMap(lambda idxBits: ((x ^ self.comparand) >> idxBits) != 0)[pgLevel]))

    def pgLevelMap(self, f):
        return list(map(lambda i: f(pgIdxBits + (pgLevels - 1 - i) * pgLevelBits),
            [i for i in range(pgLevel)]))

    def rangeHomogeneous(self, x: U, pgLevel: U, prev: PMP):
        beginsAfterLower = not (x < prev.self.comparand)
        beginsAfterUpper = not (x < self.comparand)

        pgMask = self.pgLevelMap(lambda idxBits: U(max(((BigInt(1) << pself.addrBits) - (BigInt(1) << idxBits)), 0)))[pgLevel]
        endsBeforeLower = (x & pgMask) < (prev.self.comparand & pgMask)
        endsBeforeUpper = (x & pgMask) < (self.comparand & pgMask)

        return endsBeforeLower | beginsAfterUpper | (beginsAfterLower & endsBeforeUpper)

    # returns whether this PMP completely contains, or contains none of, a page
    def homogeneous(self, x: U, pgLevel: U, prev: PMP):
        return Mux(self.napot, 
                   self.pow2Homogeneous(x, pgLevel), 
                   ~self.torNotNAPOT | self.rangeHomogeneous(x, pgLevel, prev))

    # returns whether this matching PMP fully contains the access
    def aligned(self, x: U, lgSize: U, lgMaxSize: int, prev: PMP):
        if (lgMaxSize <= pmpGranularity.log2):
            return Bool(True)

        lsbMask = UIntToOH1(lgSize, lgMaxSize)
        straddlesLowerBound = ((x >> lgMaxSize) ^ (prev.self.comparand >> lgMaxSize)) == 0 & (prev.self.comparand(lgMaxSize-1, 0) & ~x(lgMaxSize-1, 0)) != 0
        straddlesUpperBound = ((x >> lgMaxSize) ^ (self.comparand >> lgMaxSize)) == 0 & (self.comparand(lgMaxSize-1, 0) & (x(lgMaxSize-1, 0) | lsbMask)) != 0
        rangeAligned = ~(straddlesLowerBound | straddlesUpperBound)
        pow2Aligned = (lsbMask & ~self.mask[lgMaxSize-1: 0]) == 0
        return Mux(napot, pow2Aligned, rangeAligned)

    # returns whether this PMP matches at least one byte of the access
    def hit(self, x: U, lgSize: U, lgMaxSize: int, prev: PMP):
        return Mux(self.napot, 
                   self.pow2Match(x, lgSize, lgMaxSize),
                   self.torNotNAPOT & self.rangeMatch(x, lgSize, lgMaxSize, prev))

    lgAlign = 2


if __name__ == "__main__":
    pmp = PMP()
