# See LICENSE.SiFive for license details.
from pyhcl import *
from pyhcl.util import *
from typing import Union, List
from diplomacy.Parameters import AddressSet
from tilelink.Parameters import TLSlaveParameters, TLSlavePortParameters
from helper.test import *


class Parameters:
    pass


# This adapter converts between diplomatic TileLink and non-diplomatic HellaCacheIO
def ScratchpadSlavePort(address: Union[List[AddressSet], AddressSet], coreDataBytes: int, usingAtomics: bool, p: Parameters):
    if isinstance(address, AddressSet):
        address = [address]

    class clsScratchpadSlavePort(Module):

        # device = SimpleDevice("dtim", vec("sifive,dtim0"))
        node = TLManagerNode(vec(TLSlavePortParameters.v1(
            vec(TLSlaveParameters.v1(
                address            = address,
                resources          = device.reg("mem"),
                regionType         = RegionType.IDEMPOTENT,
                executable         = True,
                supportsArithmetic = TransferSizes(4, coreDataBytes) if (usingAtomics) else TransferSizes(),
                supportsLogical    = TransferSizes(4, coreDataBytes) if (usingAtomics) else TransferSizes(),
                supportsPutPartial = TransferSizes(1, coreDataBytes),
                supportsPutFull    = TransferSizes(1, coreDataBytes),
                supportsGet        = TransferSizes(1, coreDataBytes),
                fifoId             = Some(0))), # requests handled in FIFO order
            beatBytes = coreDataBytes,
            minLatency = 1)))

        io = IO(
            dmem=HellaCacheIO()
        )

        # assert(coreDataBytes * 8 == io.dmem.resp.bits.data.getWidth, "ScratchpadSlavePort is misconfigured: coreDataBytes must match D$ data width")

        (tl_in, edge) = node._in(0)

        s_ready = U(1)
        s_wait1 = U(2)
        s_wait2 = U(3)
        s_replay = U(4)
        s_grant = U(5)

        state = RegInit(s_ready)
        dmem_req_valid = Wire(Bool())
        with when (state == s_wait1): state <<= s_wait2 
        with when (io.dmem.resp.valid): state <<= s_grant 
        with when (tl_in.d.fire()): state <<= s_ready 
        with when (io.dmem.s2_nack): state <<= s_replay 
        with when (dmem_req_valid & io.dmem.req.ready): state <<= s_wait1 

        acq = Reg(tl_in.a.bits)
        with when (tl_in.a.fire()): acq <<= tl_in.a.bits 

        def formCacheReq(a: TLBundleA):
            req = Wire(HellaCacheReq)
            req.cmd <<= MuxLookup(a.opcode, Wire(M_XRD), Array(
                (TLMessages.PutFullData      , M_XWR),
                (TLMessages.PutPartialData   , M_PWR),
                (TLMessages.ArithmeticData   , MuxLookup(a.param, Wire(M_XRD), Array(
                    (TLAtomics.MIN             , M_XA_MIN),
                    (TLAtomics.MAX             , M_XA_MAX),
                    (TLAtomics.MINU            , M_XA_MINU),
                    (TLAtomics.MAXU            , M_XA_MAXU),
                    (TLAtomics.ADD             , M_XA_ADD)))),
                (TLMessages.LogicalData      , MuxLookup(a.param, Wire(M_XRD), Array(
                    (TLAtomics.XOR             , M_XA_XOR),
                    (TLAtomics.OR              , M_XA_OR),
                    (TLAtomics.AND             , M_XA_AND),
                    (TLAtomics.SWAP            , M_XA_SWAP)))),
                (TLMessages.Get              , M_XRD)))
            req.size <<= a.size
            req.signed <<= Bool(False)
            req.addr <<= a.address
            req.tag <<= U(0)
            req.phys <<= Bool(True)
            req.no_xcpt <<= Bool(True)
            return req

        # ready_likely assumes that a valid response in s_wait2 is the vastly
        # common case.  In the uncommon case, we'll erroneously send a request,
        # then s1_kill it the following cycle.
        ready_likely = state == s_ready | state == s_wait2
        ready = state == s_ready | state == s_wait2 & io.dmem.resp.valid & tl_in.d.ready
        dmem_req_valid <<= (tl_in.a.valid & ready) | state == s_replay
        dmem_req_valid_likely = (tl_in.a.valid & ready_likely) | state == s_replay

        io.dmem.req.valid <<= dmem_req_valid_likely
        tl_in.a.ready <<= io.dmem.req.ready & ready
        io.dmem.req.bits <<= f|mCacheReq(Mux(state == s_replay, acq, tl_in.a.bits))
        io.dmem.s1_data.data <<= acq.data
        io.dmem.s1_data.mask <<= acq.mask
        io.dmem.s1_kill <<= state != s_wait1
        io.dmem.s2_kill <<= Bool(False)

        tl_in.d.valid <<= io.dmem.resp.valid | state == s_grant
        tl_in.d.bits <<= Mux(acq.opcode.isOneOf(TLMessages.PutFullData, TLMessages.PutPartialData),
          edge.AccessAck(acq),
          edge.AccessAck(acq, U(0)))
        tl_in.d.bits.data <<= io.dmem.resp.bits.data_raw.holdUnless(state == s_wait2)

        # Tie off unused channels
        tl_in.b.valid <<= Bool(False)
        tl_in.c.ready <<= Bool(True)
        tl_in.e.ready <<= Bool(True)


    return clsScratchpadSlavePort()


if __name__ == "__main__":
    Emitter.dump(Emitter.emit(SimpleHellaCacheIF()), f"{__file__}.fir")

