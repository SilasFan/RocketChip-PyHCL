from pyhcl import *
from tile.Core import *
from helper.common import *
from helper.test import *


class PRV:
    SZ = 2
    U = 0
    S = 1
    H = 2
    M = 3


class MStatus(Bundle):

    def __init__(self):
        Bundle.__init__(self,
            # not truly part of mstatus, but convenient
            debug = Bool,
            cease = Bool,
            wfi = Bool,
            isa = U.w(32),
            dprv = U.w(PRV.SZ), # effective privilege for data accesses,
            prv = U.w(PRV.SZ), # not truly part of mstatus, but convenient,
            sd = Bool,
            zero2 = U.w(27),
            sxl = U.w(2),
            uxl = U.w(2),
            sd_rv32 = Bool,
            zero1 = U.w(8),
            tsr = Bool,
            tw = Bool,
            tvm = Bool,
            mxr = Bool,
            sum = Bool,
            mprv = Bool,
            xs = U.w(2),
            fs = U.w(2),
            mpp = U.w(2),
            vs = U.w(2),
            spp = U.w(1),
            mpie = Bool,
            hpie = Bool,
            spie = Bool,
            upie = Bool,
            mie = Bool,
            hie = Bool,
            sie = Bool,
            uie = Bool,
        )


class PTBR(CoreBundle):

    def __init__(self):
        if xLen == 32:
            modeBits, maxASIdBits = 1, 9
        elif xLen == 64:
            modeBits, maxASIdBits = 4, 16

        assert modeBits + maxASIdBits + maxPAddrBits - pgIdxBits == xLen

        CoreBundle.__init__(self,
            mode = U.w(modeBits),
            asid = U.w(maxASIdBits),
            ppn = U.w(maxPAddrBits - pgIdxBits),
        )

    def additionalPgLevels(self):
        return self.mode[log2Ceil(pgLevels-minPgLevels+1)-1: 0]

    def pgLevelsToMode(self, i: int):
        if (xLen, i) == (32, 2):
            return 1
        elif xLen == 64 and i >= 3 and i <= 6:
            return i + 5


if __name__ == "__main__":
    ptbr = PTBR()
