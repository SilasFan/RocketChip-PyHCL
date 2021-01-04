from pyhcl import *
from pyhcl.util import Decoupled
from tile.Core import *
from helper.test import *
from helper.common import *
from rocket.CSR import *


class HasL1HellaCacheParameters:
    pass


class AlignmentExceptions(Bundle):
    def __init__(self):
        Bundle.__init__(self,
            ld = Bool,
            st = Bool,
        )


class HasCoreData(HasCoreParameters):
    def __init__(self):
        self.data = U.w(coreDataBits)
        self.mask = U.w(coreDataBytes)


class HasCoreMemOp(HasCoreParameters):
    def __init__(self):
        self.addr = U.w(coreMaxAddrBits)
        self.tag  = U.w(coreParams.dcacheReqTagBits + log2Ceil(dcacheArbPorts))
        self.cmd  = U.w(M_SZ)
        self._size = U.w(log2Ceil(log2(coreDataBytes) + 1))
        self.signed = Bool
        self.dprv = U.w(PRV.SZ)


class HellaCacheExceptions(Bundle):
    def __init__(self):
        Bundle.__init__(self,
            ma = AlignmentExceptions(),
            pf = AlignmentExceptions(),
            ae = AlignmentExceptions(),
        )


class HellaCacheReqInternal(CoreBundle, HasCoreMemOp):
    def __init__(self, **kwargs):
        CoreBundle.__init__(self,
            phys = Bool,
            no_alloc = Bool,
            no_xcpt = Bool,
            **HasCoreMemOp().__dict__,
            **kwargs
        )


class HellaCacheWriteData(CoreBundle):
    pass


class HellaCacheReq(HellaCacheReqInternal, HasCoreData):
    def __init__(self):
        HellaCacheReqInternal.__init__(self,
            **HasCoreData().__dict__,
        )


class HellaCacheResp(CoreBundle, HasCoreMemOp, HasCoreData):
    def __init__(self):
        CoreBundle.__init__(self,
            **HasCoreData().__dict__,
            **HasCoreMemOp().__dict__,
            replay = Bool,
            has_data = Bool,
            data_word_bypass = U.w(coreDataBits),
            data_raw = U.w(coreDataBits),
            store_data = U.w(coreDataBits),
        )


class HellaCacheIO(CoreBundle):
    def __init__(self):
        CoreBundle.__init__(self,
            req = Decoupled(HellaCacheReq()),
            s1_kill = Bool, # OUTPUT # kill previous cycle's req,
            s1_data = HellaCacheWriteData(), # .asOutput # data for previous cycle's req,
            s2_nack = Bool, # INPUT # req from two cycles ago is rejected,
            s2_nack_cause_raw = Bool, # INPUT # reason for nack is store-load RAW hazard (performance hint),
            s2_kill = Bool, # OUTPUT # kill req from two cycles ago,
            s2_uncached = Bool, # INPUT # advisory signal that the access is MMIO,
            s2_paddr = U(paddrBits), # translated address,

            resp = Valid(HellaCacheResp()), #.flip,
            replay_next = Bool, # INPUT
            s2_xcpt = (HellaCacheExceptions()), # .asInput,
            uncached_resp = Decoupled(HellaCacheResp()), # TODO tileParams.dcache.get.separateUncachedResp.option(Decoupled(HellaCacheResp).flip),
            ordered = Bool, # INPUT
            # perf = HellaCachePerfEvents(), # .asInput,

            keep_clock_enabled = Bool, # OUTPUT # should D$ avoid clock-gating itself?,
            clock_enabled = Bool, # INPUT # is D$ currently being clocked?,
        )

if __name__ == "__main__":
    a = HellaCacheIO()
